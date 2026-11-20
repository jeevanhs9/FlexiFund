"""Small helpers shared by finance and dashboard route handlers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Type

from flask import jsonify, request
from pydantic import BaseModel, ValidationError


def success_response(data: Any, status_code: int = 200):
    return jsonify({"status": "success", "data": data}), status_code


def error_response(message: str, status_code: int = 400):
    return jsonify({"status": "error", "message": message}), status_code


def json_amount(value: Decimal) -> int | float:
    """Encode money as a JSON number after decimal arithmetic is complete."""
    amount = value.quantize(Decimal("0.01"))
    if amount == amount.to_integral_value():
        return int(amount)
    return float(amount)


def parse_json_body(schema: Type[BaseModel]) -> tuple[BaseModel | None, str | None]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."
    try:
        return schema.model_validate(payload), None
    except ValidationError as exc:
        return None, validation_message(exc)


def validation_message(error: ValidationError) -> str:
    details = error.errors()
    first = details[0]
    field = str(first.get("loc", ["value"])[-1])
    error_type = first.get("type")
    if field == "amount" and error_type in {"greater_than", "greater_than_equal"}:
        return "Amount must be greater than zero."
    if field == "date":
        return "Date must use the YYYY-MM-DD format."
    if error_type == "missing":
        return f"Missing required field: {field}."
    if field == "category":
        return "Invalid category. Choose a supported expense category."
    if field == "expense_type":
        return "Invalid expense_type. Choose Essential or Non-Essential."
    if field == "income_type":
        return "Invalid income_type. Choose a supported income type."
    if field == "user_id":
        return "user_id must be a positive integer."
    return f"Invalid {field}: {first.get('msg', 'value is not valid')}."


def parse_integer_filter(
    raw_value: str | None,
    field_name: str,
    *,
    minimum: int,
    maximum: int,
) -> tuple[int | None, str | None]:
    if raw_value is None:
        return None, None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be an integer."
    if not minimum <= value <= maximum:
        return None, f"{field_name} must be between {minimum} and {maximum}."
    return value, None


def parse_period_filters(
    *,
    month_value: str | None,
    year_value: str | None,
    default_current_month: bool = False,
    default_current_year: bool = False,
) -> tuple[date | None, date | None, int | None, int | None, str | None]:
    month, error = parse_integer_filter(month_value, "month", minimum=1, maximum=12)
    if error:
        return None, None, None, None, error
    year, error = parse_integer_filter(year_value, "year", minimum=1900, maximum=9998)
    if error:
        return None, None, None, None, error

    today = date.today()
    if month is not None and year is None:
        year = today.year
    elif default_current_month and month is None and year is None:
        month, year = today.month, today.year
    elif default_current_year and year is None:
        year = today.year

    if month is None and year is None:
        return None, None, month, year, None
    if month is None:
        return date(year, 1, 1), date(year + 1, 1, 1), month, year, None

    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end, month, year, None


