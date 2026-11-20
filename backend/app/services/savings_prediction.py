"""Savings estimates derived only from observed values and the cash-flow forecast."""

from __future__ import annotations

from decimal import Decimal


def predict_savings(monthly: list[dict], forecast: dict) -> dict:
    average = (
        sum((row["surplus"] for row in monthly), Decimal("0")) / len(monthly)
        if monthly else None
    )
    observed_with_income = [row for row in monthly if row["total_income"] > 0]
    latest_rate = (
        observed_with_income[-1]["savings_rate"] if observed_with_income else None
    )
    available = bool(forecast["available"] and forecast["predicted_income"] > 0)
    predicted_savings = forecast["predicted_savings"] if available else None
    predicted_rate = (
        (predicted_savings / forecast["predicted_income"] * Decimal("100")).quantize(Decimal("0.01"))
        if available else None
    )
    trend = "insufficient_history"
    if len(monthly) >= 2:
        current, previous = monthly[-1]["surplus"], monthly[-2]["surplus"]
        current_key = (monthly[-1]["year"], monthly[-1]["month_number"])
        previous_key = (monthly[-2]["year"], monthly[-2]["month_number"])
        expected = (current_key[0] - 1, 12) if current_key[1] == 1 else (current_key[0], current_key[1] - 1)
        if previous_key == expected:
            trend = "increasing" if current > previous else "decreasing" if current < previous else "stable"
    return {
        "average_monthly_savings": average.quantize(Decimal("0.01")) if average is not None else None,
        "current_savings_rate": latest_rate,
        "predicted_next_month_savings": predicted_savings,
        "predicted_savings_rate": predicted_rate,
        "savings_trend": trend,
        "potential_negative_cash_flow": bool(available and predicted_savings < 0),
        "available": available,
        "explanation": "Derived as predicted income minus predicted expenses using the cash-flow forecast." if available else "Savings prediction is unavailable because the cash-flow forecast is unavailable or predicted income is zero.",
    }
