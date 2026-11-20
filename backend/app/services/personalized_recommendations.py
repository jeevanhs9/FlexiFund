"""Actionable recommendations from measured Phase 5 and Phase 7 outputs."""

from __future__ import annotations

from decimal import Decimal


def build_personalized_recommendations(
    snapshot: dict,
    profile: dict,
    behavior: dict,
    budget: dict,
    goals: dict,
) -> dict:
    if not profile["available"]:
        return {
            "available": False,
            "recommendations": [],
            "insufficient_data": ["Not enough historical financial data is available to generate personalized actions yet."],
        }

    items = []
    risk = snapshot["overview"]["risk"]
    average_expenses = profile["average_monthly_expenses"]
    for row in budget["category_budgets"]:
        impact = row["potential_monthly_improvement"]
        if impact is None or impact <= 0:
            continue
        items.append(
            {
                "title": f"Review {row['category']} spending",
                "explanation": f"Returning this month’s recorded {row['category']} spending to its recent observed average could improve monthly cash flow by about ₹{impact:,.2f}.",
                "reason": row["reason"],
                "supporting_metric": {
                    "current_spending": row["current_spending"],
                    "historical_average": row["historical_average"],
                    "recommended_amount": row["recommended_amount"],
                    "basis_months": row["basis_months"],
                },
                "estimated_impact": {"monthly_cash_flow": impact, "annual_if_repeated": impact * Decimal("12"), "status": "projected"},
                "priority": "high" if (
                    risk["band"] in {"Critical", "Needs Attention"}
                    or (average_expenses is not None and average_expenses > 0 and impact >= average_expenses * Decimal("0.10"))
                ) else "medium",
                "action": {"type": "reduce_category_to_observed_average", "category": row["category"], "amount": impact},
            }
        )

    risk_actions = {
        "Negative Cash Flow": ("Review this month’s recorded cash-flow gap", "Compare upcoming bills with recorded income and pause optional spending until the gap is understood."),
        "Low Savings Rate": ("Review a savings buffer", "Use the observed monthly surplus and essential expenses to choose a manageable buffer; the current record does not establish future capacity."),
        "High Expense Ratio": ("Check major monthly costs", "Review the largest recorded expense categories and confirm whether the current month is representative."),
        "High Discretionary Spending": ("Review optional spending", "Look at recorded non-essential expenses and choose any reductions that fit your needs."),
        "Income Volatility": ("Plan around variable income", "Use a lower-income month in your planning and keep recurring commitments within that range."),
        "Declining Savings": ("Review the falling surplus trend", "Compare the last three consecutive recorded months before setting a new goal contribution."),
        "High Spending Volatility": ("Check what changed between months", "Review the recorded expense pattern and identify whether the variation comes from one-off costs."),
    }
    for factor in risk["risk_factors"]:
        title, action_text = risk_actions.get(factor["factor"], (f"Review {factor['factor'].casefold()}", factor["message"]))
        items.append(
            {
                "title": title,
                "explanation": factor["message"],
                "reason": "This factor is part of the Phase 5 explainable financial-risk calculation.",
                "supporting_metric": {"factor": factor["factor"], "value": factor["value"], "severity": factor["severity"]},
                "estimated_impact": None,
                "priority": "high" if factor["severity"] in {"high", "critical"} else "medium",
                "action": {"type": "review_financial_pattern", "guidance": action_text},
            }
        )

    for trend in behavior["category_trends"]:
        if trend["status"] != "increasing":
            continue
        items.append(
            {
                "title": f"Check the recent rise in {trend['category']}",
                "explanation": f"Recorded {trend['category']} spending changed from ₹{trend['previous_amount']:,.2f} to ₹{trend['current_amount']:,.2f} between the latest observed months.",
                "reason": "The change is calculated from the two latest observed month totals; no savings impact is assumed.",
                "supporting_metric": trend,
                "estimated_impact": None,
                "priority": "medium",
                "action": {"type": "review_category", "category": trend["category"]},
            }
        )

    for recurring in behavior["recurring_expenses"]:
        items.append(
            {
                "title": f"Review recurring {recurring['category']} costs",
                "explanation": f"FlexiFund detected a recurring pattern averaging ₹{recurring['average_amount']:,.2f} in {recurring['category']}; review whether the amount and timing are expected.",
                "reason": f"Pattern detected from {recurring['occurrences']} observed transactions with {recurring['confidence']} confidence.",
                "supporting_metric": recurring,
                "estimated_impact": None,
                "priority": "low",
                "action": {"type": "review_recurring_cost", "category": recurring["category"]},
            }
        )

    for goal in goals["goals"]:
        if goal["status"] != "active" or goal["feasibility"] not in {"stretch_goal", "not_feasible_with_observed_surplus"}:
            continue
        items.append(
            {
                "title": f"Adjust the plan for {goal['name']}",
                "explanation": f"The required monthly amount of ₹{goal['required_monthly_savings']:,.2f} is above the observed positive monthly surplus capacity.",
                "reason": "This compares the goal’s remaining amount and time with average surplus from months that contain both income and expenses.",
                "supporting_metric": {
                    "required_monthly_savings": goal["required_monthly_savings"],
                    "observed_monthly_capacity": goals["optimization"]["observed_monthly_contribution_capacity"],
                    "target_date": goal["target_date"],
                },
                "estimated_impact": None,
                "priority": "high" if goal["priority"] == "high" else "medium",
                "action": {"type": "adjust_goal_deadline_or_target", "goal_id": goal["id"]},
            }
        )

    current_emergency = snapshot["overview"]["emergency_fund"]
    has_emergency_goal = any(
        "emergency" in goal.name.casefold() and goal.status == "active"
        for goal in snapshot["goals"]
    )
    if current_emergency["recommended_minimum"] is not None and not has_emergency_goal:
        items.append(
            {
                "title": "Consider an emergency-fund goal",
                "explanation": f"Recorded essential expenses imply a provisional three-month target of about ₹{current_emergency['recommended_minimum']:,.2f}.",
                "reason": "Phase 5 estimates this target from observed essential expenses. No current emergency-fund balance has been provided.",
                "supporting_metric": {
                    "provisional_target": current_emergency["recommended_minimum"],
                    "basis_months": current_emergency["basis_months"],
                    "current_balance": None,
                },
                "estimated_impact": None,
                "priority": "medium" if risk["band"] in {"Critical", "Needs Attention", "Moderate"} else "low",
                "action": {"type": "create_goal", "suggested_name": "Emergency fund", "suggested_target": current_emergency["recommended_minimum"]},
            }
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda item: (priority_order[item["priority"]], item["title"].casefold()))
    return {
        "available": True,
        "recommendations": items,
        "insufficient_data": [] if items else ["The available records do not support a specific personalized action yet."],
        "method": "Recommendations are generated from the Phase 5 risk, recurring-cost, spending and emergency-fund calculations, plus Phase 7 goal and budget analysis. Estimated impacts are labeled as projections and may not occur.",
    }
