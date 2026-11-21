"""Summary, monthly, and expense-category dashboard endpoints."""

from __future__ import annotations

from calendar import month_name
from collections import defaultdict
from decimal import Decimal

from flask import Blueprint, request
from sqlalchemy import select

from app.auth import authenticated_blueprint, authorize_user_id
from app.database import session_scope
from app.models import Expense, ImportedTransaction, Income, User
from app.routes.helpers import (
    error_response,
    json_amount,
    parse_period_filters,
    success_response,
)
from app.services.financial_calculator import (
    calculate_financial_summary,
    calculate_work_adjusted_net_income,
)
from app.services.financial_health import health_indicators

dashboard_bp = authenticated_blueprint(
    Blueprint("dashboard", __name__, url_prefix="/api/dashboard")
)


def _dashboard_user(session):
    user_id, error = authorize_user_id(request.args.get("user_id"))
    if error:
        return None, error
    user = session.get(User, user_id)
    if user is None:
        return None, error_response("User was not found.", 404)
    return user, None


def _period_from_request(*, default_current_month: bool = False, default_current_year: bool = False):
    start, end, month, year, error = parse_period_filters(
        month_value=request.args.get("month"),
        year_value=request.args.get("year"),
        default_current_month=default_current_month,
        default_current_year=default_current_year,
    )
    return (start, end, month, year, error)


def _date_filters(date_column, *, start, end):
    filters = []
    if start is not None:
        filters.append(date_column >= start)
    if end is not None:
        filters.append(date_column < end)
    return filters


def _response_number(key: str, value: Decimal) -> int | float:
    if key in {"savings_rate", "expense_ratio", "essential_expense_ratio", "non_essential_expense_ratio"}:
        return float(value)
    return json_amount(value)


@dashboard_bp.get("")
def get_dashboard():
    start, end, month, year, error = _period_from_request(default_current_month=True)
    if error:
        return error_response(error)

    with session_scope() as session:
        user, user_error = _dashboard_user(session)
        if user_error:
            return user_error

        income_records = session.scalars(
            select(Income)
            .where(Income.user_id == user.id, *_date_filters(Income.date, start=start, end=end))
            .order_by(Income.date)
        ).all()
        expense_records = session.scalars(
            select(Expense)
            .where(Expense.user_id == user.id, *_date_filters(Expense.date, start=start, end=end))
            .order_by(Expense.date)
        ).all()

        summary = calculate_financial_summary(income_records, expense_records)
        work_expense_records = session.scalars(
            select(ImportedTransaction).where(
                ImportedTransaction.user_id == user.id,
                ImportedTransaction.transaction_type == "Expense",
                ImportedTransaction.is_work_expense.is_(True),
                *_date_filters(ImportedTransaction.transaction_date, start=start, end=end),
            )
        ).all()
        work_expenses = sum(
            (record.amount for record in work_expense_records), start=Decimal("0.00")
        ).quantize(Decimal("0.01"))
        summary["work_expenses"] = work_expenses
        summary["work_adjusted_net_income"] = calculate_work_adjusted_net_income(
            summary["total_income"], work_expenses
        )
        summary.update(health_indicators(summary))
        data = {
            key: _response_number(key, value) if isinstance(value, Decimal) else value
            for key, value in summary.items()
        }
        data.update(
            {
                "user_id": user.id,
                "user_name": user.name,
                "period": {"month": month, "year": year},
            }
        )
    return success_response(data)


@dashboard_bp.get("/monthly")
def get_monthly_summary():
    start, end, month, year, error = _period_from_request(default_current_year=True)
    if error:
        return error_response(error)

    with session_scope() as session:
        user, user_error = _dashboard_user(session)
        if user_error:
            return user_error

        income_records = session.scalars(
            select(Income).where(
                Income.user_id == user.id,
                *_date_filters(Income.date, start=start, end=end),
            )
        ).all()
        expense_records = session.scalars(
            select(Expense).where(
                Expense.user_id == user.id,
                *_date_filters(Expense.date, start=start, end=end),
            )
        ).all()

        monthly = defaultdict(lambda: {"income": Decimal("0.00"), "expenses": Decimal("0.00")})
        for record in income_records:
            monthly[(record.date.year, record.date.month)]["income"] += record.amount
        for record in expense_records:
            monthly[(record.date.year, record.date.month)]["expenses"] += record.amount

        result = []
        for (entry_year, entry_month), totals in sorted(monthly.items()):
            income = totals["income"].quantize(Decimal("0.01"))
            expenses = totals["expenses"].quantize(Decimal("0.01"))
            result.append(
                {
                    "month": month_name[entry_month],
                    "year": entry_year,
                    "income": json_amount(income),
                    "expenses": json_amount(expenses),
                    "surplus": json_amount(income - expenses),
                }
            )
    return result


@dashboard_bp.get("/expense-categories")
def get_expense_categories():
    start, end, _month, _year, error = _period_from_request(default_current_month=True)
    if error:
        return error_response(error)

    with session_scope() as session:
        user, user_error = _dashboard_user(session)
        if user_error:
            return user_error

        records = session.scalars(
            select(Expense).where(
                Expense.user_id == user.id,
                *_date_filters(Expense.date, start=start, end=end),
            )
        ).all()
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for record in records:
            totals[record.category] += record.amount
        result = {
            category: json_amount(amount.quantize(Decimal("0.01")))
            for category, amount in sorted(totals.items())
        }
    return result
