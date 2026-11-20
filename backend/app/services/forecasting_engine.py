"""A conservative weighted moving-average forecast over completed months."""

from __future__ import annotations

from calendar import month_name
from datetime import date
from decimal import Decimal
from statistics import mean, pstdev


def _previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _weighted_mean(values: list[Decimal]) -> Decimal:
    weights = list(range(1, len(values) + 1))
    return (sum((value * weight for value, weight in zip(values, weights)), Decimal("0")) / sum(weights)).quantize(Decimal("0.01"))


def forecast_cash_flow(monthly: list[dict], *, as_of: date | None = None) -> dict:
    """Forecast next calendar month only with three contiguous completed months."""
    as_of = as_of or date.today()
    expected_previous = _previous_month(as_of.year, as_of.month)
    lookup = {(row["year"], row["month_number"]): row for row in monthly}
    chain: list[dict] = []
    cursor = expected_previous
    while cursor in lookup and len(chain) < 6:
        chain.append(lookup[cursor])
        cursor = _previous_month(*cursor)
    chain.reverse()
    target_year, target_month = _next_month(as_of.year, as_of.month)
    period = f"{target_year:04d}-{target_month:02d}"

    if len(chain) < 3:
        if not monthly:
            reason = "Add financial transactions to unlock financial intelligence."
        else:
            reason = (
                "Insufficient historical data for reliable forecasting. Add at least three consecutive completed months, including the previous month."
            )
        return {
            "available": False,
            "predicted_income": None,
            "predicted_expenses": None,
            "predicted_savings": None,
            "method": None,
            "confidence": None,
            "historical_months": len(chain),
            "historical_period": None,
            "forecast_month": month_name[target_month],
            "forecast_period": period,
            "explanation": reason,
            "inputs": [],
        }

    income = _weighted_mean([row["total_income"] for row in chain])
    expenses = _weighted_mean([row["total_expenses"] for row in chain])
    savings = (income - expenses).quantize(Decimal("0.01"))
    expense_values = [float(row["total_expenses"]) for row in chain]
    average = mean(expense_values)
    coefficient = (pstdev(expense_values) / average) if average else 0
    confidence = "medium" if len(chain) >= 4 and coefficient <= 0.35 else "low"
    first = chain[0]
    last = chain[-1]
    return {
        "available": True,
        "predicted_income": income,
        "predicted_expenses": expenses,
        "predicted_savings": savings,
        "method": "weighted_moving_average",
        "confidence": confidence,
        "historical_months": len(chain),
        "historical_period": {
            "from": f"{first['year']:04d}-{first['month_number']:02d}",
            "through": f"{last['year']:04d}-{last['month_number']:02d}",
        },
        "forecast_month": month_name[target_month],
        "forecast_period": period,
        "explanation": (
            f"Weighted moving average of {len(chain)} consecutive completed months; recent months receive higher weights. "
            f"Confidence is {confidence} based on sample count and historical expense variability, not a measured accuracy rate."
        ),
        "inputs": [f"{row['year']:04d}-{row['month_number']:02d}" for row in chain],
    }


def apply_expense_prediction(forecast: dict, expense_prediction: dict) -> dict:
    """Use a validated expense prediction while preserving the income fallback.

    The Phase 5 weighted moving average remains the fallback for accounts that
    do not have enough expense history for model validation.
    """
    if not (forecast.get("available") and expense_prediction.get("available")):
        return forecast
    result = dict(forecast)
    predicted_expenses = expense_prediction["predicted_expenses"]
    result["predicted_expenses"] = predicted_expenses
    result["predicted_savings"] = (result["predicted_income"] - predicted_expenses).quantize(Decimal("0.01"))
    result["method"] = f"weighted_moving_average_income__{expense_prediction['selected_model']}_expenses"
    result["expense_prediction"] = expense_prediction
    result["explanation"] = (
        f"Income uses the existing weighted moving average. Expenses use the validated {expense_prediction['selected_model'].replace('_', ' ')} "
        f"selection ({expense_prediction['training_observations']} training and {expense_prediction['validation_observations']} later chronological validation observations). "
        "Actual and predicted amounts remain separate; this is a statistical estimate, not a guarantee."
    )
    return result
