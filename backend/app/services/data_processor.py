"""Validate financial records before analysis without changing stored data."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class FinancialTransaction:
    """A normalized income or expense row used by the intelligence pipeline."""

    id: int | None
    user_id: int
    date: date
    amount: Decimal
    kind: str
    category: str | None = None
    expense_type: str | None = None
    description: str | None = None


def _normalized_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def prepare_transactions(
    incomes: list[Any], expenses: list[Any], user_id: int
) -> tuple[list[FinancialTransaction], dict[str, Any]]:
    """Normalize valid rows and report questionable data; retain duplicate candidates."""
    prepared: list[FinancialTransaction] = []
    invalid_count = 0
    wrong_user_count = 0
    missing_category_count = 0
    unknown_classification_count = 0
    warnings: list[str] = []

    for kind, rows in (("income", incomes), ("expense", expenses)):
        for row in rows:
            if getattr(row, "user_id", None) != user_id:
                wrong_user_count += 1
                continue
            try:
                amount = Decimal(str(getattr(row, "amount")))
                transaction_date = _normalized_date(getattr(row, "date", None))
                if not amount.is_finite() or amount <= 0 or transaction_date is None:
                    raise ValueError("invalid amount or date")
            except (InvalidOperation, TypeError, ValueError):
                invalid_count += 1
                continue

            if kind == "expense":
                category = str(getattr(row, "category", "") or "").strip()
                if not category:
                    category = "Uncategorized"
                    missing_category_count += 1
                expense_type = getattr(row, "expense_type", None)
                if expense_type not in {"Essential", "Non-Essential"}:
                    expense_type = None
                    unknown_classification_count += 1
            else:
                category = str(getattr(row, "income_type", "") or "").strip() or "Uncategorized"
                expense_type = None

            prepared.append(
                FinancialTransaction(
                    id=getattr(row, "id", None),
                    user_id=user_id,
                    date=transaction_date,
                    amount=amount.quantize(Decimal("0.01")),
                    kind=kind,
                    category=category,
                    expense_type=expense_type,
                    description=getattr(row, "description", None),
                )
            )

    fingerprints = Counter(
        (
            row.kind,
            row.date,
            row.amount,
            row.category,
            row.expense_type,
            (row.description or "").strip().casefold(),
        )
        for row in prepared
    )
    duplicate_candidates = sum(count - 1 for count in fingerprints.values() if count > 1)
    if invalid_count:
        warnings.append(f"{invalid_count} invalid row(s) were excluded from analysis.")
    if wrong_user_count:
        warnings.append(f"{wrong_user_count} row(s) for a different user were excluded.")
    if missing_category_count:
        warnings.append(f"{missing_category_count} expense row(s) have no category and are shown as Uncategorized.")
    if unknown_classification_count:
        warnings.append(f"{unknown_classification_count} expense row(s) have no recognized essentiality classification.")
    if duplicate_candidates:
        warnings.append(
            f"{duplicate_candidates} exact duplicate candidate(s) were retained; review them before deleting anything."
        )

    return prepared, {
        "input_rows": len(incomes) + len(expenses),
        "valid_rows": len(prepared),
        "invalid_rows_excluded": invalid_count,
        "wrong_user_rows_excluded": wrong_user_count,
        "missing_categories": missing_category_count,
        "unknown_expense_classifications": unknown_classification_count,
        "duplicate_candidates_retained": duplicate_candidates,
        "warnings": warnings,
    }
