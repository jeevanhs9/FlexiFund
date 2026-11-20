"""Category budget guardrails grounded in observed expense months."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal


def build_adaptive_budget(snapshot: dict, profile: dict, *, today: date | None = None) -> dict:
    today = today or date.today()
    current_key = (today.year, today.month)
    expenses = [row for row in snapshot["expenses"] if row.date <= today]
    current_spending: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    spending_by_month: dict[tuple[int, int, str], Decimal] = defaultdict(lambda: Decimal("0"))
    observed_expense_months = set()
    current_essential = Decimal("0")
    current_discretionary = Decimal("0")

    for row in expenses:
        category = row.category or "Uncategorized"
        month_key = (row.date.year, row.date.month)
        observed_expense_months.add(month_key)
        spending_by_month[(*month_key, category)] += row.amount
        if month_key == current_key:
            current_spending[category] += row.amount
            if row.expense_type == "Essential":
                current_essential += row.amount
            elif row.expense_type == "Non-Essential":
                current_discretionary += row.amount

    prior_months = sorted(month for month in observed_expense_months if month < current_key)[-3:]
    baseline_ready = len(prior_months) >= 3
    categories = sorted(current_spending, key=str.casefold)
    recommendations = []
    for category in categories:
        current = current_spending[category]
        historical_average = None
        if baseline_ready:
            historical_average = (
                sum((spending_by_month[(*month, category)] for month in prior_months), Decimal("0"))
                / Decimal(len(prior_months))
            ).quantize(Decimal("0.01"))
        target = min(current, historical_average) if baseline_ready and historical_average is not None else None
        potential = (current - target).quantize(Decimal("0.01")) if target is not None else None
        recommendations.append(
            {
                "category": category,
                "current_spending": current.quantize(Decimal("0.01")),
                "historical_average": historical_average,
                "recommended_amount": target,
                "potential_monthly_improvement": potential,
                "basis_months": len(prior_months),
                "reason": (
                    "Current spending exceeds the mean of the last observed expense months; the target returns to that observed average."
                    if potential is not None and potential > 0 else
                    "No lower target is supported by the observed history."
                    if baseline_ready and historical_average is not None else
                    "At least three prior expense months are needed for a reliable category baseline."
                ),
            }
        )

    improvements = [row["potential_monthly_improvement"] for row in recommendations if row["potential_monthly_improvement"] is not None]
    active_goals = [goal for goal in snapshot["goals"] if goal.status == "active"]
    total_goal_requirement = None
    if active_goals:
        today_month_index = today.year * 12 + today.month
        requirements = []
        for goal in active_goals:
            remaining = max(Decimal("0"), goal.target_amount - goal.current_amount)
            months = max(1, goal.target_date.year * 12 + goal.target_date.month - today_month_index)
            requirements.append(remaining / Decimal(months))
        total_goal_requirement = sum(requirements, Decimal("0")).quantize(Decimal("0.01"))

    return {
        "available": bool(current_spending),
        "selected_period": {"year": current_key[0], "month": current_key[1]},
        "as_of_date": today,
        "current_period_is_in_progress": True,
        "current_month_income": snapshot["overview"]["summary"]["total_income"],
        "current_month_expenses": sum(current_spending.values(), Decimal("0")).quantize(Decimal("0.01")),
        "current_month_surplus": snapshot["overview"]["summary"]["surplus"],
        "current_essential_expenses": current_essential.quantize(Decimal("0.01")),
        "current_discretionary_expenses": current_discretionary.quantize(Decimal("0.01")),
        "average_observed_monthly_surplus": profile["average_monthly_surplus"],
        "active_goals_required_monthly": total_goal_requirement,
        "goal_capacity_status": (
            "insufficient_data" if profile["average_monthly_surplus"] is None or total_goal_requirement is None else
            "within_observed_surplus" if total_goal_requirement <= max(Decimal("0"), profile["average_monthly_surplus"]) else
            "above_observed_surplus"
        ),
        "category_budgets": recommendations,
        "financial_health": profile["financial_health"],
        "risk_factors": profile["risk_factors"],
        "spending_trends": snapshot["overview"]["spending"]["category_trends"],
        "potential_monthly_improvement": sum(improvements, Decimal("0")).quantize(Decimal("0.01")) if baseline_ready else None,
        "potential_annual_improvement": (sum(improvements, Decimal("0")) * Decimal("12")).quantize(Decimal("0.01")) if baseline_ready else None,
        "baseline_available": baseline_ready,
        "baseline_months": [f"{year:04d}-{month:02d}" for year, month in prior_months],
        "insufficient_data": [] if baseline_ready else ["Not enough historical financial data is available to set reliable adaptive category budgets yet."],
        "method": "Targets require three prior observed expense months and are capped at their average. Current-month figures are recorded-to-date; goals, available surplus, financial-health indicators, essential/discretionary mix, and Phase 5 category trends are included as planning context. Missing calendar months are not treated as zero, and no generic percentage cut is applied.",
    }
