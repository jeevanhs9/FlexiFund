"""User, income, and expense APIs."""

from __future__ import annotations

from typing import Any, get_args

from flask import Blueprint, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth import (
    authenticated_blueprint,
    authenticated_user_id,
    authorize_body_user_id,
    authorize_user_id,
)
from app.database import session_scope
from app.models import Expense, Income, User
from app.schemas import ExpenseCategory, ExpenseCreate, IncomeCreate, UserCreate
from app.routes.helpers import (
    error_response,
    json_amount,
    parse_json_body,
    parse_period_filters,
    success_response,
)

finance_bp = authenticated_blueprint(Blueprint("finance", __name__, url_prefix="/api"))


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


def _record_filters(
    model: type[Income] | type[Expense],
    *,
    user_id: int,
    start: Any,
    end: Any,
) -> list[Any]:
    filters = [model.user_id == user_id]
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
    authorization_error = authorize_body_user_id(body.user_id)
    if authorization_error:
        return authorization_error

    with session_scope() as session:
        record = Income(
            user_id=authenticated_user_id(),
            **body.model_dump(exclude={"user_id"}),
        )
        session.add(record)
        session.flush()
        result = _serialize_income(record)
    return success_response(result, 201)


@finance_bp.get("/income")
def get_income():
    start, end, _month, _year, error = parse_period_filters(
        month_value=request.args.get("month"),
        year_value=request.args.get("year"),
    )
    if error:
        return error_response(error)

    user_id, error = authorize_user_id(request.args.get("user_id"))
    if error:
        return error
    with session_scope() as session:
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
    authorization_error = authorize_body_user_id(body.user_id)
    if authorization_error:
        return authorization_error

    with session_scope() as session:
        record = Expense(
            user_id=authenticated_user_id(),
            **body.model_dump(exclude={"user_id"}),
        )
        session.add(record)
        session.flush()
        result = _serialize_expense(record)
    return success_response(result, 201)


@finance_bp.get("/expenses")
def get_expenses():
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

    user_id, error = authorize_user_id(request.args.get("user_id"))
    if error:
        return error
    with session_scope() as session:
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
