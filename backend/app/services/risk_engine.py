"""Transparent, coverage-aware financial health scoring and risk factors."""

from __future__ import annotations

from decimal import Decimal
from statistics import mean, pstdev

WEIGHTS = {
    "savings_rate": 20,
    "expense_ratio": 20,
    "cash_flow_stability": 15,
    "income_stability": 10,
    "essential_expense_ratio": 10,
    "discretionary_spending": 10,
    "spending_volatility": 10,
    "savings_trend": 5,
}


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def score_financial_risk(
    monthly: list[dict], spending: dict, *, expense_prediction: dict | None = None
) -> dict:
    """Score financial resilience from 0–100 and disclose observed component coverage."""
    if not monthly:
        return {
            "score": None,
            "band": "insufficient_data",
            "coverage_percent": 0.0,
            "components": [],
            "positive_factors": [],
            "negative_factors": [],
            "risk_factors": [],
            "explanation": "No financial history is available to calculate a score.",
        }

    components: dict[str, tuple[float, float, object]] = {}
    income_months = [row for row in monthly if row["total_income"] > 0]
    if income_months:
        avg_rate = mean(float(row["savings_rate"]) for row in income_months)
        avg_expense_ratio = mean(float(row["expense_ratio"]) for row in income_months)
        components["savings_rate"] = (_clamp(50 + avg_rate * 2), WEIGHTS["savings_rate"], round(avg_rate, 2))
        components["expense_ratio"] = (_clamp(100 - max(0, avg_expense_ratio - 50) * 1.5), WEIGHTS["expense_ratio"], round(avg_expense_ratio, 2))

    if len(monthly) >= 2:
        positive_ratio = sum(row["surplus"] >= 0 for row in monthly) / len(monthly) * 100
        components["cash_flow_stability"] = (positive_ratio, WEIGHTS["cash_flow_stability"], round(positive_ratio, 2))

    if len(income_months) >= 3:
        incomes = [float(row["total_income"]) for row in income_months]
        cv = pstdev(incomes) / mean(incomes) if mean(incomes) else 0
        components["income_stability"] = (_clamp(100 - cv * 100), WEIGHTS["income_stability"], round(cv * 100, 2))

    classified_expenses = [row for row in monthly if row["total_expenses"] > 0]
    if classified_expenses:
        essential_ratio = mean(float(row["essential_expense_ratio"]) for row in classified_expenses)
        discretionary_ratio = mean(float(row["non_essential_expense_ratio"]) for row in classified_expenses)
        components["essential_expense_ratio"] = (_clamp(100 - max(0, essential_ratio - 60) * 1.5), WEIGHTS["essential_expense_ratio"], round(essential_ratio, 2))
        components["discretionary_spending"] = (_clamp(100 - discretionary_ratio * 1.25), WEIGHTS["discretionary_spending"], round(discretionary_ratio, 2))

    volatility = spending.get("spending_volatility_percent")
    if volatility is not None:
        components["spending_volatility"] = (_clamp(100 - float(volatility)), WEIGHTS["spending_volatility"], float(volatility))

    if len(monthly) >= 2:
        last, before = monthly[-1]["surplus"], monthly[-2]["surplus"]
        last_key = (monthly[-1]["year"], monthly[-1]["month_number"])
        previous_key = (monthly[-2]["year"], monthly[-2]["month_number"])
        expected = (last_key[0] - 1, 12) if last_key[1] == 1 else (last_key[0], last_key[1] - 1)
        if previous_key == expected:
            trend_score = 80 if last > before else 60 if last == before else 35
            components["savings_trend"] = (trend_score, WEIGHTS["savings_trend"], "increasing" if last > before else "stable" if last == before else "decreasing")

    observed_weight = sum(weight for _score, weight, _value in components.values())
    score = round(sum(value * weight for value, weight, _ in components.values()) / observed_weight) if observed_weight else None
    coverage = round(observed_weight, 1)
    if score is None:
        band = "insufficient_data"
    elif score >= 80:
        band = "Excellent"
    elif score >= 65:
        band = "Healthy"
    elif score >= 50:
        band = "Moderate"
    elif score >= 30:
        band = "Needs Attention"
    else:
        band = "Critical"

    component_rows = [
        {"name": name, "score": round(value, 1), "weight": weight, "observed_value": observed}
        for name, (value, weight, observed) in components.items()
    ]
    positive = []
    negative = []
    factors = []
    latest = monthly[-1]
    latest_income = latest["total_income"]
    if latest["surplus"] < 0:
        factors.append({"factor": "Negative Cash Flow", "severity": "critical", "value": float(latest["surplus"]), "message": "Recorded expenses exceed recorded income in the latest observed month."})
    elif latest["surplus"] > 0:
        positive.append("Positive cash flow in the latest observed month.")
    if latest_income > 0:
        rate = float(latest["savings_rate"])
        if rate < 10:
            factors.append({"factor": "Low Savings Rate", "severity": "high", "value": rate, "message": "Less than 10% of recorded income remained after expenses."})
        elif rate >= 20:
            positive.append("Savings rate was at least 20% in the latest observed month.")
        ratio = float(latest["expense_ratio"])
        if ratio >= 80:
            factors.append({"factor": "High Expense Ratio", "severity": "high", "value": ratio, "message": "Recorded expenses consumed at least 80% of recorded income."})
    if latest["total_expenses"] > 0 and float(latest["non_essential_expense_ratio"]) >= 35:
        discretionary_ratio = float(latest["non_essential_expense_ratio"])
        factors.append({"factor": "High Discretionary Spending", "severity": "medium", "value": discretionary_ratio, "message": "At least 35% of recorded expenses were classified as non-essential in the latest observed month."})
    if len(income_months) >= 3:
        cv_value = components.get("income_stability", (0, 0, 0))[2]
        if isinstance(cv_value, (int, float)) and cv_value >= 30:
            factors.append({"factor": "Income Volatility", "severity": "medium", "value": cv_value, "message": "Monthly recorded income has a coefficient of variation of at least 30%."})
    three_months = monthly[-3:] if len(monthly) >= 3 else []
    consecutive_three = False
    if len(three_months) == 3:
        consecutive_three = all(
            (right["year"], right["month_number"])
            == ((left["year"] + (1 if left["month_number"] == 12 else 0)), left["month_number"] % 12 + 1)
            for left, right in zip(three_months, three_months[1:])
        )
    if consecutive_three and monthly[-1]["surplus"] < monthly[-2]["surplus"] < monthly[-3]["surplus"]:
        factors.append({"factor": "Declining Savings", "severity": "high", "value": "three_month_downtrend", "message": "Recorded monthly savings decreased for three consecutive observations."})
    if len(monthly) >= 2 and float(volatility or 0) >= 30:
        factors.append({"factor": "High Spending Volatility", "severity": "medium", "value": float(volatility), "message": "Observed monthly expenses vary substantially relative to their average."})
    prediction_context = None
    if expense_prediction and expense_prediction.get("available"):
        predicted_change = expense_prediction["predicted_change_from_latest"]
        prediction_context = {
            "forecast_period": expense_prediction["forecast_period"],
            "selected_model": expense_prediction["selected_model"],
            "predicted_change_from_latest": predicted_change,
            "predicted_change_percent": expense_prediction["predicted_change_percent"],
        }
        if predicted_change >= Decimal("250") and (expense_prediction["predicted_change_percent"] or 0) >= Decimal("10"):
            factors.append({
                "factor": "Projected Expense Increase",
                "severity": "medium",
                "value": float(predicted_change),
                "message": "The validated next-month expense estimate is materially above the latest recorded monthly expenses. This is a projection, not a recorded result.",
            })
    if not factors and positive:
        positive.append("No high-severity risk factor was found in the observed data.")

    return {
        "score": score,
        "band": band,
        "coverage_percent": coverage,
        "components": component_rows,
        "positive_factors": positive,
        "negative_factors": [factor["message"] for factor in factors],
        "risk_factors": factors,
        "expense_prediction_context": prediction_context,
        "explanation": "Component scores are weighted and normalized across available data; missing history is excluded and reflected in coverage. This is an explainable budgeting indicator, not a credit score.",
    }
