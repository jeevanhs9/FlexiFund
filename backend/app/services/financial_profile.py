"""Dynamic financial profiles derived from the user's records and Phase 5."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal


def build_financial_profile(snapshot: dict) -> dict:
    overview = snapshot["overview"]
    monthly = overview["features"]["monthly_history"]
    income_months = [row for row in monthly if row["total_income"] > 0]
    expense_months = [row for row in monthly if row["total_expenses"] > 0]
    cash_flow_months = [row for row in monthly if row["total_income"] > 0 and row["total_expenses"] > 0]
    average_income = _average([row["total_income"] for row in income_months])
    average_expenses = _average([row["total_expenses"] for row in expense_months])
    average_surplus = _average([row["surplus"] for row in cash_flow_months])
    average_savings_rate = _average([row["savings_rate"] for row in cash_flow_months])
    average_essential = _average([row["essential_expenses"] for row in expense_months])
    average_discretionary = _average([row["non_essential_expenses"] for row in expense_months])
    essential_ratio = _ratio(average_essential, average_expenses)
    discretionary_ratio = _ratio(average_discretionary, average_expenses)
    savings_consistency = (
        Decimal(sum(row["surplus"] > 0 for row in cash_flow_months))
        / Decimal(len(cash_flow_months))
        * Decimal("100")
        if cash_flow_months else None
    )

    category_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for expense in snapshot["expenses"]:
        if expense.date <= date.today():
            category_totals[expense.category or "Uncategorized"] += expense.amount
    total_recorded_expenses = sum(category_totals.values(), Decimal("0"))
    top_categories = [
        {
            "category": category,
            "amount": amount.quantize(Decimal("0.01")),
            "share_percent": _ratio(amount, total_recorded_expenses),
        }
        for category, amount in sorted(category_totals.items(), key=lambda item: (-item[1], item[0].casefold()))[:5]
    ]

    risk = overview["risk"]
    income_stability = next(
        (row["observed_value"] for row in risk["components"] if row["name"] == "income_stability"),
        None,
    )
    volatility = overview["spending"]["spending_volatility_percent"]
    recurring_total = sum(
        (
            row["average_amount"] if row["frequency"] == "monthly" else
            row["average_amount"] * Decimal("4.33") if row["frequency"] == "weekly" else
            Decimal("0")
            for row in overview["recurring"]
        ),
        Decimal("0"),
    )
    recurring_ratio = _ratio(recurring_total, average_expenses)
    active_goals = [goal for goal in snapshot["goals"] if goal.status == "active"]
    goal_progress = _average(
        [min(Decimal("100"), goal.current_amount / goal.target_amount * Decimal("100")) for goal in active_goals]
    )

    data_ready = bool(overview["data_quality"]["valid_rows"])
    return {
        "available": data_ready,
        "period_count": len(monthly),
        "income_month_count": len(income_months),
        "expense_month_count": len(expense_months),
        "cash_flow_month_count": len(cash_flow_months),
        "record_count": overview["data_quality"]["valid_rows"],
        "average_monthly_income": average_income,
        "average_monthly_expenses": average_expenses,
        "average_monthly_surplus": average_surplus,
        "average_savings_rate_percent": average_savings_rate,
        "essential_expense_ratio_percent": essential_ratio,
        "discretionary_expense_ratio_percent": discretionary_ratio,
        "income_variation_percent": income_stability,
        "spending_volatility_percent": volatility,
        "recurring_expense_ratio_percent": recurring_ratio,
        "savings_consistency_percent": savings_consistency,
        "average_active_goal_progress_percent": goal_progress,
        "active_goal_count": len(active_goals),
        "top_spending_categories": top_categories,
        "financial_health": {"score": risk["score"], "band": risk["band"], "coverage_percent": risk["coverage_percent"]},
        "risk_factors": risk["risk_factors"],
        "insufficient_data": _profile_gaps(data_ready, income_months, expense_months, cash_flow_months),
    }


def _average(values):
    return sum(values, Decimal("0")) / Decimal(len(values)) if values else None


def _ratio(numerator, denominator):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return (numerator / denominator * Decimal("100")).quantize(Decimal("0.01"))


def _profile_gaps(data_ready, income_months, expense_months, cash_flow_months):
    gaps = []
    if not data_ready:
        return ["Add income or expense records to build a financial profile."]
    if not income_months:
        gaps.append("Recorded income is not available for an income average.")
    if not expense_months:
        gaps.append("Recorded expenses are not available for an expense average.")
    if not cash_flow_months:
        gaps.append("A monthly surplus and savings rate need income and expenses recorded in the same month.")
    return gaps
