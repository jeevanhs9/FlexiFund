"""Financial intelligence APIs backed by the selected user's finance rows."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from app.auth import authenticated_blueprint, authorize_user_id
from app.database import session_scope
from app.models import Expense, Income, User
from app.routes.helpers import error_response, json_amount, parse_period_filters
from app.services.intelligence_service import build_intelligence_overview

intelligence_bp = authenticated_blueprint(
    Blueprint("intelligence", __name__, url_prefix="/api/intelligence")
)


def _json_safe(value: Any, key: str = "") -> Any:
    if isinstance(value, Decimal):
        if any(part in key for part in ("rate", "ratio", "percent", "change")):
            return float(value)
        return json_amount(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(child_key): _json_safe(child, str(child_key)) for child_key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(child, key) for child in value]
    return value


def _selected_user(session):
    user_id, error = authorize_user_id(request.args.get("user_id"))
    if error:
        return None, error
    user = session.get(User, user_id)
    if user is None:
        return None, error_response("User was not found.", 404)
    return user, None


def _period():
    _start, _end, month, year, error = parse_period_filters(
        month_value=request.args.get("month"), year_value=request.args.get("year")
    )
    return month, year, error


def _overview_for_request():
    month, year, error = _period()
    if error:
        return None, error
    with session_scope() as session:
        user, user_error = _selected_user(session)
        if user_error:
            return None, user_error
        # The selected account is derived from the authenticated session. A query
        # string user_id can only repeat that identity, never choose another user.
        incomes = session.scalars(
            select(Income).where(Income.user_id == user.id).order_by(Income.date, Income.id)
        ).all()
        expenses = session.scalars(
            select(Expense).where(Expense.user_id == user.id).order_by(Expense.date, Expense.id)
        ).all()
        result = build_intelligence_overview(
            incomes, expenses, user_id=user.id, month=month, year=year
        )
    result["user_name"] = user.name
    return result, None


def _respond(key: str | None = None):
    result, error = _overview_for_request()
    if error:
        return error
    data = result if key is None else result[key]
    return jsonify(
        {
            "status": "success",
            "data": _json_safe(data),
            "generated_at": result["generated_at"],
        }
    )


@intelligence_bp.get("/overview")
def get_overview():
    return _respond()


@intelligence_bp.get("/forecast")
def get_forecast():
    return _respond("forecast")


@intelligence_bp.get("/expense-prediction")
def get_expense_prediction():
    return _respond("expense_prediction")


@intelligence_bp.get("/spending")
def get_spending():
    return _respond("spending")


@intelligence_bp.get("/anomalies")
def get_anomalies():
    return _respond("anomalies")


@intelligence_bp.get("/recurring")
def get_recurring():
    return _respond("recurring")


@intelligence_bp.get("/risk")
def get_risk():
    return _respond("risk")


@intelligence_bp.get("/recommendations")
def get_recommendations():
    return _respond("recommendations")


@intelligence_bp.get("/savings")
def get_savings():
    return _respond("savings")
