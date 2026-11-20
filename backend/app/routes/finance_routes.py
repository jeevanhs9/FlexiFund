"""User, income, and expense APIs."""

from __future__ import annotations

from typing import Any, get_args

from flask import Blueprint, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import session_scope
from app.models import Expense, Income, User
from app.schemas import ExpenseCategory, ExpenseCreate, IncomeCreate, UserCreate
from app.routes.helpers import (
    error_response,
    json_amount,
    parse_integer_filter,
    parse_json_body,
    parse_period_filters,
    success_response,
)

finance_bp = Blueprint("finance", __name__, url_prefix="/api")


def _created_at(record: Any) -> str:
    return record.created_at.isoformat()


def _serialize_income(record: Income) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "source": record.source,
        "amount": json_amount(record.amount),
        "income_type": record.income_type,
        "date": record.date.isoformat(),
        "description": record.description,
        "created_at": _created_at(record),
    }


def _serialize_expense(record: Expense) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "category": record.category,
        "amount": json_amount(record.amount),
        "expense_type": record.expense_type,
        "date": record.date.isoformat(),
        "description": record.description,
        "created_at": _created_at(record),
    }


def _optional_user_id(raw_user_id: str | None) -> tuple[int | None, str | None]:
    return parse_integer_filter(raw_user_id, "user_id", minimum=1, maximum=2_147_483_647)


def _record_filters(
    model: type[Income] | type[Expense],
    *,
    user_id: int | None,
    start: Any,
    end: Any,
) -> list[Any]:
    filters = []
    if user_id is not None:
        filters.append(model.user_id == user_id)
    if start is not None:
        filters.append(model.date >= start)
    if end is not None:
        filters.append(model.date < end)
    return filters


@finance_bp.post("/users")
def create_user():
    body, error = parse_json_body(UserCreate)
    if error:
        return error_response(error)

    user_data = body.model_dump()
    try:
        with session_scope() as session:
            user = User(**user_data)
            session.add(user)
            session.flush()
            result = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "created_at": _created_at(user),
            }
    except IntegrityError:
        return error_response("A user with this email already exists.", 409)
    return success_response(result, 201)


@finance_bp.post("/income")
def create_income():
    body, error = parse_json_body(IncomeCreate)
    if error:
        return error_response(error)

    with session_scope() as session:
        user = session.get(User, body.user_id)
        if user is None:
            return error_response("User was not found.", 404)
        record = Income(**body.model_dump())
        session.add(record)
        session.flush()
        result = _serialize_income(record)
    return success_response(result, 201)


@finance_bp.get("/income")
def get_income():
    user_id, error = _optional_user_id(request.args.get("user_id"))
    if error:
        return error_response(error)
    start, end, _month, _year, error = parse_period_filters(
        month_value=request.args.get("month"),
        year_value=request.args.get("year"),
    )
    if error:
        return error_response(error)

    with session_scope() as session:
        if user_id is not None and session.get(User, user_id) is None:
            return error_response("User was not found.", 404)
        statement = (
            select(Income)
            .where(*_record_filters(Income, user_id=user_id, start=start, end=end))
            .order_by(Income.date.desc(), Income.id.desc())
        )
        records = session.scalars(statement).all()
        result = [_serialize_income(record) for record in records]
    return success_response(result)


@finance_bp.post("/expenses")
def create_expense():
    body, error = parse_json_body(ExpenseCreate)
    if error:
        return error_response(error)

    from app.database import session_scope

    with session_scope() as session:
        user = session.get(User, body.user_id)
        if user is None:
            return error_response("User was not found.", 404)
        record = Expense(**body.model_dump())
        session.add(record)
        session.flush()
        result = _serialize_expense(record)
    return success_response(result, 201)


@finance_bp.get("/expenses")
def get_expenses():
    user_id, error = _optional_user_id(request.args.get("user_id"))
    if error:
        return error_response(error)
    start, end, _month, _year, error = parse_period_filters(
        month_value=request.args.get("month"),
        year_value=request.args.get("year"),
    )
    if error:
        return error_response(error)

    category = request.args.get("category")
    if category is not None and category not in get_args(ExpenseCategory):
        return error_response("Invalid category. Choose a supported expense category.")
    expense_type = request.args.get("expense_type")
    if expense_type is not None and expense_type not in {"Essential", "Non-Essential"}:
        return error_response("Invalid expense_type. Choose Essential or Non-Essential.")

    with session_scope() as session:
        if user_id is not None and session.get(User, user_id) is None:
            return error_response("User was not found.", 404)
        filters = _record_filters(Expense, user_id=user_id, start=start, end=end)
        if category is not None:
            filters.append(Expense.category == category)
        if expense_type is not None:
            filters.append(Expense.expense_type == expense_type)
        records = session.scalars(
            select(Expense).where(*filters).order_by(Expense.date.desc(), Expense.id.desc())
        ).all()
        result = [_serialize_expense(record) for record in records]
    return success_response(result)
