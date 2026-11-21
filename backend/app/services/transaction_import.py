"""Safe, modular CSV statement ingestion for user-owned financial records.

The parser deliberately does not persist source files or raw rows. It returns a
normalised representation which the import service can preview or save. Future
JSON, PDF, and authorised-account adapters can feed the same normalised shape.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
import json
from io import StringIO
from pathlib import Path
import re
import secrets
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Expense,
    ImportBatch,
    ImportedTransaction,
    Income,
    TransactionClassificationPreference,
)


SUPPORTED_FIELDS = {
    "transaction_date",
    "description",
    "debit",
    "credit",
    "amount",
    "balance",
    "reference_id",
    "payment_mode",
}

COLUMN_ALIASES = {
    "transaction_date": (
        "date", "transaction date", "txn date", "value date", "date of transaction",
    ),
    "description": (
        "description", "narration", "transaction", "particulars", "remarks", "details",
    ),
    "debit": (
        "debit", "dr", "withdrawal", "amount debited", "debit amount", "withdrawals",
    ),
    "credit": (
        "credit", "cr", "deposit", "amount credited", "credit amount", "deposits",
    ),
    "amount": ("amount", "transaction amount", "txn amount"),
    "balance": ("balance", "closing balance", "closing bal", "available balance"),
    "reference_id": (
        "transaction id", "txn id", "reference number", "reference no", "ref no", "utr", "rrn",
    ),
    "payment_mode": ("payment mode", "mode", "channel", "transaction mode"),
}

ESSENTIAL_CATEGORIES = {
    "Food", "Rent", "Transportation", "Utilities", "EMI", "Healthcare", "Education", "Insurance",
}


class StatementValidationError(ValueError):
    """Raised for a user-fixable file or row validation problem."""


@dataclass(frozen=True)
class Classification:
    transaction_type: str
    category: str | None
    subcategory: str | None
    is_work_expense: bool
    confidence: str
    needs_review: bool


@dataclass(frozen=True)
class NormalizedTransaction:
    transaction_date: date
    description: str
    amount: Decimal
    debit: Decimal | None
    credit: Decimal | None
    balance: Decimal | None
    reference_id: str | None
    payment_mode: str | None
    row_number: int
    duplicate_fingerprint: str
    classification: Classification


@dataclass
class ParsedStatement:
    mapping: dict[str, str]
    headers: list[str] = field(default_factory=list)
    transactions: list[NormalizedTransaction] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    total_nonempty_rows: int = 0


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def merchant_key(description: str) -> str:
    """Return a stable, non-sensitive key used only for user corrections."""
    scrubbed = re.sub(r"\b\d{4,}\b", "", description.casefold())
    scrubbed = re.sub(r"[^a-z0-9]+", " ", scrubbed).strip()
    return scrubbed[:180] or "unlabelled transaction"


def _optional_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] if text else None


def _money(value: Any, *, field_name: str, required: bool = False) -> Decimal | None:
    if value is None or not str(value).strip():
        if required:
            raise StatementValidationError(f"{field_name} is required")
        return None
    text = str(value).strip().replace(",", "")
    text = re.sub(r"^(?:₹|rs\.?|inr)\s*", "", text, flags=re.IGNORECASE)
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("() ")
    try:
        result = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise StatementValidationError(f"{field_name} must be a valid amount") from exc
    if negative:
        result = -result
    if not result.is_finite():
        raise StatementValidationError(f"{field_name} must be a finite amount")
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_date(value: Any) -> date:
    text = str(value or "").strip()
    if not text:
        raise StatementValidationError("date is required")
    for date_format in (
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y", "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    raise StatementValidationError("date must use a recognised format such as YYYY-MM-DD or DD/MM/YYYY")


def resolve_mapping(headers: Iterable[str], supplied_mapping: dict[str, str] | None = None) -> dict[str, str]:
    """Map recognised bank headers to the internal normalisation fields."""
    original_headers = [header for header in headers if header and header.strip()]
    if not original_headers:
        raise StatementValidationError("The CSV must include a header row.")
    by_key = {_header_key(header): header for header in original_headers}
    mapping: dict[str, str] = {}
    explicitly_set: set[str] = set()
    if supplied_mapping:
        for internal_name, csv_header in supplied_mapping.items():
            if internal_name not in SUPPORTED_FIELDS:
                raise StatementValidationError(f"Unsupported mapping field: {internal_name}")
            explicitly_set.add(internal_name)
            if not str(csv_header or "").strip():
                continue
            if csv_header not in original_headers:
                raise StatementValidationError(f"Mapped CSV column was not found: {csv_header}")
            mapping[internal_name] = csv_header
    for internal_name, aliases in COLUMN_ALIASES.items():
        if internal_name in mapping or internal_name in explicitly_set:
            continue
        for alias in aliases:
            header = by_key.get(_header_key(alias))
            if header:
                mapping[internal_name] = header
                break
    if "transaction_date" not in mapping:
        raise StatementValidationError(
            "The CSV does not contain a recognizable date column. Expected examples: Date, Transaction Date, or Txn Date."
        )
    if not any(name in mapping for name in ("debit", "credit", "amount")):
        raise StatementValidationError(
            "The CSV must contain a Debit/Credit pair or an Amount column."
        )
    return mapping


def _decode_csv(data: bytes) -> str:
    if not data:
        raise StatementValidationError("The CSV file is empty.")
    if b"\x00" in data:
        raise StatementValidationError("The CSV contains unsupported binary data.")
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise StatementValidationError("The CSV encoding is unsupported. Save the statement as UTF-8 CSV and try again.")


def _fingerprint(
    transaction_date: date,
    description: str,
    amount: Decimal,
    debit: Decimal | None,
    credit: Decimal | None,
    balance: Decimal | None,
    payment_mode: str | None,
) -> str:
    # Balance and direction distinguish common same-day, same-merchant repeats.
    parts = (
        transaction_date.isoformat(),
        merchant_key(description),
        str(amount),
        str(debit or ""),
        str(credit or ""),
        str(balance or ""),
        (payment_mode or "").casefold(),
    )
    return sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _rule_classification(
    *, description: str, debit: Decimal | None, credit: Decimal | None, preference: TransactionClassificationPreference | None,
) -> Classification:
    if preference is not None:
        return Classification(
            transaction_type=preference.transaction_type,
            category=preference.category,
            subcategory=None,
            is_work_expense=preference.is_work_expense,
            confidence="high",
            needs_review=False,
        )

    text = description.casefold()
    transfer_terms = ("own account", "self transfer", "account transfer", "transfer to self", "transfer from self")
    if any(term in text for term in transfer_terms):
        return Classification("Transfer", None, None, False, "medium", False)

    if debit is not None and debit > 0:
        category = "Other"
        subcategory = None
        confidence = "low"
        needs_review = True
        is_work_expense = False
        rules = (
            (("swiggy", "zomato", "restaurant", "cafe", "food", "dining"), "Food", None, "high", False),
            (("hp petrol", "indian oil", "bharat petroleum", "petrol", "fuel", "diesel"), "Transportation", "Fuel", "medium", True),
            (("uber", "ola", "rapido", "metro", "railway", "bus", "travel"), "Transportation", None, "high", False),
            (("rent", "landlord"), "Rent", None, "high", False),
            (("electricity", "water bill", "broadband", "internet bill", "gas bill"), "Utilities", None, "high", False),
            (("emi", "loan repayment", "loan emi"), "EMI", None, "high", False),
            (("hospital", "pharmacy", "medical", "clinic"), "Healthcare", None, "high", False),
            (("netflix", "spotify", "movie", "cinema"), "Entertainment", None, "high", False),
            (("school", "college", "course", "tuition", "udemy"), "Education", None, "high", False),
            (("insurance", "policy premium"), "Insurance", None, "high", False),
            (("amazon", "flipkart", "myntra", "shopping"), "Shopping", None, "medium", False),
        )
        for terms, selected_category, selected_subcategory, selected_confidence, selected_review in rules:
            if any(term in text for term in terms):
                category, subcategory = selected_category, selected_subcategory
                confidence, needs_review = selected_confidence, selected_review
                break
        work_terms = (
            "platform fee", "delivery partner", "driver partner", "vehicle service", "vehicle maintenance",
            "garage", "tyre", "work equipment", "commercial permit",
        )
        if any(term in text for term in work_terms):
            is_work_expense, confidence, needs_review = True, "high", False
        return Classification("Expense", category, subcategory, is_work_expense, confidence, needs_review)

    if credit is not None and credit > 0:
        income_terms = ("salary", "payroll", "client payment", "freelance", "consulting", "gig payout", "delivery payout", "driver payout")
        if any(term in text for term in income_terms):
            return Classification("Income", None, None, False, "high", False)
        # A credit can be a refund, a self transfer, loan drawdown, or income.
        # It remains reviewable until there is positive evidence it is income.
        return Classification("Unknown", None, None, False, "low", True)

    return Classification("Unknown", None, None, False, "low", True)


def parse_statement_csv(
    filename: str,
    content: bytes,
    *,
    supplied_mapping: dict[str, str] | None = None,
    preferences: dict[str, TransactionClassificationPreference] | None = None,
    max_rows: int = 5000,
) -> ParsedStatement:
    """Validate and normalize one uploaded CSV without writing to the database."""
    if Path(filename).suffix.casefold() != ".csv":
        raise StatementValidationError("Only .csv bank statement files can be imported.")
    text = _decode_csv(content)
    reader = csv.DictReader(StringIO(text, newline=""))
    headers = [header for header in (reader.fieldnames or []) if header and header.strip()]
    mapping = resolve_mapping(headers, supplied_mapping)
    parsed = ParsedStatement(mapping=mapping, headers=headers)
    preferences = preferences or {}
    for row_number, row in enumerate(reader, start=2):
        if parsed.total_nonempty_rows >= max_rows:
            raise StatementValidationError(f"The CSV exceeds the {max_rows}-row import limit.")
        if not any(str(value or "").strip() for value in row.values()):
            continue
        parsed.total_nonempty_rows += 1
        try:
            transaction_date = _parse_date(row.get(mapping["transaction_date"]))
            description = _optional_text(row.get(mapping.get("description", "")), 500) or ""
            debit = _money(row.get(mapping.get("debit", "")), field_name="debit")
            credit = _money(row.get(mapping.get("credit", "")), field_name="credit")
            raw_amount = _money(row.get(mapping.get("amount", "")), field_name="amount")
            balance = _money(row.get(mapping.get("balance", "")), field_name="balance")
            if debit is not None and debit < 0:
                debit = abs(debit)
            if credit is not None and credit < 0:
                credit = abs(credit)
            if debit and credit:
                raise StatementValidationError("debit and credit cannot both contain a positive amount")
            if debit:
                amount = debit
            elif credit:
                amount = credit
            elif raw_amount is not None and raw_amount != 0:
                amount = abs(raw_amount)
                # An unsigned Amount column alone does not establish direction.
                debit = abs(raw_amount) if raw_amount < 0 else None
                credit = None
            else:
                raise StatementValidationError("a positive debit, credit, or amount is required")
            reference_id = _optional_text(row.get(mapping.get("reference_id", "")), 160)
            payment_mode = _optional_text(row.get(mapping.get("payment_mode", "")), 80)
            preference = preferences.get(merchant_key(description))
            classification = _rule_classification(
                description=description, debit=debit, credit=credit, preference=preference
            )
            parsed.transactions.append(
                NormalizedTransaction(
                    transaction_date=transaction_date,
                    description=description,
                    amount=amount,
                    debit=debit,
                    credit=credit,
                    balance=balance,
                    reference_id=reference_id,
                    payment_mode=payment_mode,
                    row_number=row_number,
                    duplicate_fingerprint=_fingerprint(
                        transaction_date, description, amount, debit, credit, balance, payment_mode
                    ),
                    classification=classification,
                )
            )
        except StatementValidationError as exc:
            parsed.errors.append({"row": row_number, "message": str(exc)})
    if parsed.total_nonempty_rows == 0:
        raise StatementValidationError("The CSV does not contain any transaction rows.")
    if not parsed.transactions:
        raise StatementValidationError("No valid transactions were found in the CSV. Check the date and amount columns.")
    return parsed


def load_user_preferences(session: Session, user_id: int) -> dict[str, TransactionClassificationPreference]:
    rows = session.scalars(
        select(TransactionClassificationPreference).where(TransactionClassificationPreference.user_id == user_id)
    ).all()
    return {row.merchant_key: row for row in rows}


def _batch_code() -> str:
    return f"FB-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}"


def _expense_type(category: str | None) -> str:
    return "Essential" if category in ESSENTIAL_CATEGORIES else "Non-Essential"


def sync_analysis_record(session: Session, record: ImportedTransaction) -> None:
    """Make an imported classification available to the existing financial engine."""
    if record.transaction_type == "Income":
        if record.linked_expense_id:
            linked_expense = session.get(Expense, record.linked_expense_id)
            if linked_expense is not None:
                session.delete(linked_expense)
            record.linked_expense_id = None
        income = session.get(Income, record.linked_income_id) if record.linked_income_id else None
        if income is None:
            income = Income(
                user_id=record.user_id,
                source=(record.description or "Imported bank statement")[:120],
                amount=record.amount,
                income_type="Freelance" if any(word in record.description.casefold() for word in ("client", "freelance", "consult")) else "Other",
                date=record.transaction_date,
                description=record.description or None,
            )
            session.add(income)
            session.flush()
            record.linked_income_id = income.id
        else:
            income.source = (record.description or "Imported bank statement")[:120]
            income.amount = record.amount
            income.date = record.transaction_date
            income.description = record.description or None
        return

    if record.transaction_type == "Expense":
        if record.linked_income_id:
            linked_income = session.get(Income, record.linked_income_id)
            if linked_income is not None:
                session.delete(linked_income)
            record.linked_income_id = None
        expense = session.get(Expense, record.linked_expense_id) if record.linked_expense_id else None
        if expense is None:
            expense = Expense(
                user_id=record.user_id,
                category=record.category or "Other",
                amount=record.amount,
                expense_type=_expense_type(record.category),
                date=record.transaction_date,
                description=record.description or None,
            )
            session.add(expense)
            session.flush()
            record.linked_expense_id = expense.id
        else:
            expense.category = record.category or "Other"
            expense.amount = record.amount
            expense.expense_type = _expense_type(record.category)
            expense.date = record.transaction_date
            expense.description = record.description or None
        return

    # Transfer and unknown rows are retained for review but correctly excluded
    # from Income/Expense-derived dashboard and ML calculations.
    if record.linked_income_id:
        linked_income = session.get(Income, record.linked_income_id)
        if linked_income is not None:
            session.delete(linked_income)
        record.linked_income_id = None
    if record.linked_expense_id:
        linked_expense = session.get(Expense, record.linked_expense_id)
        if linked_expense is not None:
            session.delete(linked_expense)
        record.linked_expense_id = None


def process_statement_import(
    session: Session,
    *,
    user_id: int,
    filename: str,
    parsed: ParsedStatement,
) -> ImportBatch:
    """Create an import batch, skip exact duplicates, and sync classified rows."""
    clean_filename = Path(filename).name[:255] or "bank-statement.csv"
    batch = ImportBatch(
        batch_code=_batch_code(),
        user_id=user_id,
        filename=clean_filename,
        mapping_json=json.dumps(parsed.mapping, sort_keys=True),
        total_rows=parsed.total_nonempty_rows,
        rejected_rows=len(parsed.errors),
    )
    session.add(batch)
    session.flush()

    references = {row.reference_id for row in parsed.transactions if row.reference_id}
    fingerprints = {row.duplicate_fingerprint for row in parsed.transactions}
    existing_reference_ids = set()
    if references:
        existing_reference_ids = set(session.scalars(
            select(ImportedTransaction.reference_id).where(
                ImportedTransaction.user_id == user_id,
                ImportedTransaction.reference_id.in_(references),
            )
        ).all())
    existing_fingerprints = set(session.scalars(
        select(ImportedTransaction.duplicate_fingerprint).where(
            ImportedTransaction.user_id == user_id,
            ImportedTransaction.duplicate_fingerprint.in_(fingerprints),
        )
    ).all())

    for normalized in parsed.transactions:
        if (
            (normalized.reference_id and normalized.reference_id in existing_reference_ids)
            or normalized.duplicate_fingerprint in existing_fingerprints
        ):
            batch.duplicate_rows += 1
            continue
        classification = normalized.classification
        record = ImportedTransaction(
            user_id=user_id,
            import_batch_id=batch.id,
            transaction_date=normalized.transaction_date,
            description=normalized.description,
            amount=normalized.amount,
            transaction_type=classification.transaction_type,
            debit=normalized.debit,
            credit=normalized.credit,
            balance=normalized.balance,
            payment_mode=normalized.payment_mode,
            reference_id=normalized.reference_id,
            category=classification.category,
            subcategory=classification.subcategory,
            is_work_expense=classification.is_work_expense,
            classification_confidence=classification.confidence,
            review_status="needs_review" if classification.needs_review else "classified",
            source="csv",
            duplicate_fingerprint=normalized.duplicate_fingerprint,
        )
        session.add(record)
        session.flush()
        sync_analysis_record(session, record)
        batch.imported_rows += 1
        if record.review_status == "needs_review":
            batch.review_rows += 1
        if normalized.reference_id:
            existing_reference_ids.add(normalized.reference_id)
        # Do not use newly seen fallback fingerprints to suppress another row
        # in this same statement: two legitimate cash-like transactions can
        # have identical visible fields. Existing persisted rows are the only
        # fallback-deduplication candidates.
    return batch


def apply_user_correction(
    session: Session,
    record: ImportedTransaction,
    *,
    transaction_type: str | None = None,
    category: str | None = None,
    is_work_expense: bool | None = None,
) -> ImportedTransaction:
    """Persist a user correction and remember it for the same merchant text."""
    if transaction_type is not None:
        record.transaction_type = transaction_type
    if category is not None:
        record.category = category
    if is_work_expense is not None:
        record.is_work_expense = is_work_expense
    if record.transaction_type != "Expense":
        record.category = None
        record.subcategory = None
        record.is_work_expense = False
    elif not record.category:
        record.category = "Other"
    record.classification_confidence = "high"
    record.review_status = "corrected"
    sync_analysis_record(session, record)

    key = merchant_key(record.description)
    preference = session.scalar(
        select(TransactionClassificationPreference).where(
            TransactionClassificationPreference.user_id == record.user_id,
            TransactionClassificationPreference.merchant_key == key,
        )
    )
    if preference is None:
        preference = TransactionClassificationPreference(
            user_id=record.user_id,
            merchant_key=key,
            category=record.category,
            transaction_type=record.transaction_type,
            is_work_expense=record.is_work_expense,
        )
        session.add(preference)
    else:
        preference.category = record.category
        preference.transaction_type = record.transaction_type
        preference.is_work_expense = record.is_work_expense
    return record
