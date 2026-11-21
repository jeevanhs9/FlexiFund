"""Authenticated CSV statement preview, import, and correction APIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, request
from sqlalchemy import func, select

from app.auth import authenticated_blueprint, authenticated_user_id
from app.database import session_scope
from app.models import ImportBatch, ImportedTransaction
from app.routes.helpers import error_response, json_amount, parse_json_body, success_response
from app.schemas import ImportedTransactionUpdate
from app.services.transaction_import import (
    SUPPORTED_FIELDS,
    StatementValidationError,
    apply_user_correction,
    load_user_preferences,
    parse_statement_csv,
    process_statement_import,
)


transaction_import_bp = authenticated_blueprint(
    Blueprint("transaction_import", __name__, url_prefix="/api/transactions")
)


def _batch_json(batch: ImportBatch) -> dict[str, Any]:
    return {
        "id": batch.id,
        "batch_code": batch.batch_code,
        "filename": batch.filename,
        "source": batch.source,
        "total_rows": batch.total_rows,
        "imported_rows": batch.imported_rows,
        "duplicate_rows": batch.duplicate_rows,
        "rejected_rows": batch.rejected_rows,
        "review_rows": batch.review_rows,
        "created_at": batch.created_at.isoformat(),
    }


def _transaction_json(record: ImportedTransaction) -> dict[str, Any]:
    return {
        "id": record.id,
        "import_batch_id": record.import_batch_id,
        "transaction_date": record.transaction_date.isoformat(),
        "description": record.description,
        "amount": json_amount(record.amount),
        "transaction_type": record.transaction_type,
        "debit": json_amount(record.debit) if record.debit is not None else None,
        "credit": json_amount(record.credit) if record.credit is not None else None,
        "balance": json_amount(record.balance) if record.balance is not None else None,
        "payment_mode": record.payment_mode,
        "reference_id": record.reference_id,
        "category": record.category,
        "subcategory": record.subcategory,
        "is_work_expense": record.is_work_expense,
        "is_recurring": record.is_recurring,
        "classification_confidence": record.classification_confidence,
        "review_status": record.review_status,
        "source": record.source,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _preview_json(row) -> dict[str, Any]:
    return {
        "row": row.row_number,
        "transaction_date": row.transaction_date.isoformat(),
        "description": row.description,
        "amount": json_amount(row.amount),
        "debit": json_amount(row.debit) if row.debit is not None else None,
        "credit": json_amount(row.credit) if row.credit is not None else None,
        "reference_id": row.reference_id,
        "payment_mode": row.payment_mode,
        "transaction_type": row.classification.transaction_type,
        "category": row.classification.category,
        "subcategory": row.classification.subcategory,
        "is_work_expense": row.classification.is_work_expense,
        "classification_confidence": row.classification.confidence,
        "needs_review": row.classification.needs_review,
    }


def _upload_payload() -> tuple[str, bytes, dict[str, str] | None] | tuple[None, None, None]:
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return None, None, None
    filename = Path(uploaded.filename).name
    max_bytes = int(current_app.config["MAX_BANK_CSV_BYTES"])
    content = uploaded.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise StatementValidationError(
            f"The CSV exceeds the {max_bytes // 1024} KB upload limit."
        )
    supplied_mapping = None
    mapping_text = request.form.get("mapping")
    if mapping_text:
        try:
            candidate = json.loads(mapping_text)
        except json.JSONDecodeError as exc:
            raise StatementValidationError("The supplied column mapping is invalid.") from exc
        if not isinstance(candidate, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in candidate.items()
        ):
            raise StatementValidationError("The supplied column mapping is invalid.")
        supplied_mapping = candidate
    return filename, content, supplied_mapping


def _parse_uploaded_statement():
    filename, content, supplied_mapping = _upload_payload()
    if filename is None or content is None:
        return None, error_response("Choose a CSV bank statement to continue.")
    with session_scope() as session:
        preferences = load_user_preferences(session, authenticated_user_id())
    try:
        parsed = parse_statement_csv(
            filename,
            content,
            supplied_mapping=supplied_mapping,
            preferences=preferences,
            max_rows=int(current_app.config["MAX_BANK_CSV_ROWS"]),
        )
    except StatementValidationError as exc:
        return None, error_response(str(exc))
    return (filename, parsed), None


@transaction_import_bp.post("/preview")
def preview_statement():
    """Validate and normalize a CSV in memory; source content is not retained."""
    result, error = _parse_uploaded_statement()
    if error:
        return error
    _filename, parsed = result
    preview_rows = [_preview_json(row) for row in parsed.transactions[:50]]
    return success_response(
        {
            "headers": parsed.headers,
            "mapping": parsed.mapping,
            "supported_fields": sorted(SUPPORTED_FIELDS),
            "total_rows": parsed.total_nonempty_rows,
            "valid_rows": len(parsed.transactions),
            "rejected_rows": len(parsed.errors),
            "requires_review": sum(row.classification.needs_review for row in parsed.transactions),
            "errors": parsed.errors[:50],
            "transactions": preview_rows,
            "preview_truncated": len(parsed.transactions) > len(preview_rows),
            "notice": "This is a CSV preview only. FlexiFund does not keep the source file.",
        }
    )


@transaction_import_bp.post("/import")
def import_statement():
    """Persist a validated CSV batch and its non-duplicate normalized rows."""
    result, error = _parse_uploaded_statement()
    if error:
        return error
    filename, parsed = result
    with session_scope() as session:
        batch = process_statement_import(
            session, user_id=authenticated_user_id(), filename=filename, parsed=parsed
        )
        session.flush()
        data = _batch_json(batch)
    return success_response(data, 201)


@transaction_import_bp.get("")
@transaction_import_bp.get("/")
def list_imported_transactions():
    """Return the signed-in user's imported rows; never another account's data."""
    review_only = request.args.get("review_only", "").casefold() in {"1", "true", "yes"}
    with session_scope() as session:
        filters = [ImportedTransaction.user_id == authenticated_user_id()]
        if review_only:
            filters.append(ImportedTransaction.review_status == "needs_review")
        rows = session.scalars(
            select(ImportedTransaction)
            .where(*filters)
            .order_by(ImportedTransaction.transaction_date.desc(), ImportedTransaction.id.desc())
            .limit(200)
        ).all()
        result = [_transaction_json(row) for row in rows]
    return success_response(result)


@transaction_import_bp.get("/imports")
def list_import_batches():
    with session_scope() as session:
        batches = session.scalars(
            select(ImportBatch)
            .where(ImportBatch.user_id == authenticated_user_id())
            .order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
            .limit(100)
        ).all()
        result = [_batch_json(batch) for batch in batches]
    return success_response(result)


def _owned_batch(session, batch_id: int) -> ImportBatch | None:
    return session.scalar(
        select(ImportBatch).where(
            ImportBatch.id == batch_id,
            ImportBatch.user_id == authenticated_user_id(),
        )
    )


@transaction_import_bp.get("/imports/<int:batch_id>")
def get_import_batch(batch_id: int):
    with session_scope() as session:
        batch = _owned_batch(session, batch_id)
        if batch is None:
            return error_response("Import batch was not found.", 404)
        result = _batch_json(batch)
    return success_response(result)


@transaction_import_bp.get("/imports/<int:batch_id>/transactions")
def get_imported_transactions(batch_id: int):
    review_only = request.args.get("review_only", "").casefold() in {"1", "true", "yes"}
    with session_scope() as session:
        batch = _owned_batch(session, batch_id)
        if batch is None:
            return error_response("Import batch was not found.", 404)
        filters = [
            ImportedTransaction.import_batch_id == batch.id,
            ImportedTransaction.user_id == authenticated_user_id(),
        ]
        if review_only:
            filters.append(ImportedTransaction.review_status == "needs_review")
        rows = session.scalars(
            select(ImportedTransaction)
            .where(*filters)
            .order_by(ImportedTransaction.transaction_date.desc(), ImportedTransaction.id.desc())
        ).all()
        result = [_transaction_json(row) for row in rows]
    return success_response(result)


@transaction_import_bp.patch("/imported/<int:transaction_id>")
def correct_imported_transaction(transaction_id: int):
    body, error = parse_json_body(ImportedTransactionUpdate)
    if error:
        return error_response(error)
    with session_scope() as session:
        record = session.scalar(
            select(ImportedTransaction).where(
                ImportedTransaction.id == transaction_id,
                ImportedTransaction.user_id == authenticated_user_id(),
            )
        )
        if record is None:
            return error_response("Imported transaction was not found.", 404)
        apply_user_correction(session, record, **body.model_dump(exclude_unset=True))
        batch = session.get(ImportBatch, record.import_batch_id)
        if batch is not None:
            batch.review_rows = int(session.scalar(
                select(func.count()).select_from(ImportedTransaction).where(
                    ImportedTransaction.import_batch_id == batch.id,
                    ImportedTransaction.review_status == "needs_review",
                )
            ) or 0)
        session.flush()
        result = _transaction_json(record)
    return success_response(result)
