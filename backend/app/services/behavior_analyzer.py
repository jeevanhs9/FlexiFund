"""Explainable behavior patterns based on observed months and Phase 5 signals."""

from __future__ import annotations

from calendar import month_name
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal


def _consecutive(left: dict, right: dict) -> bool:
    month = left["month_number"] % 12 + 1
    year = left["year"] + (1 if left["month_number"] == 12 else 0)
    return (right["year"], right["month_number"]) == (year, month)


def _goal_start_date(goal) -> date | None:
    created = getattr(goal, "created_at", None)
    if isinstance(created, datetime):
        return created.date()
    return created if isinstance(created, date) else None


def build_behavior_analysis(snapshot: dict, profile: dict) -> dict:
    overview = snapshot["overview"]
    monthly = overview["features"]["monthly_history"]
    insights = []
    monthly_trend = {"status": "insufficient_data", "current_amount": None, "previous_amount": None, "change_percent": None}
    if len(monthly) >= 2 and _consecutive(monthly[-2], monthly[-1]):
        previous = monthly[-2]["total_expenses"]
        current = monthly[-1]["total_expenses"]
        change = ((current - previous) / abs(previous) * Decimal("100")).quantize(Decimal("0.01")) if previous else None
        status = "increasing" if current > previous else "decreasing" if current < previous else "stable"
        monthly_trend = {"status": status, "current_amount": current, "previous_amount": previous, "change_percent": change}

    increasing_streak = False
    decreasing_streak = False
    if len(monthly) >= 3 and all(_consecutive(left, right) for left, right in zip(monthly[-3:], monthly[-2:])):
        amounts = [row["total_expenses"] for row in monthly[-3:]]
        increasing_streak = amounts[0] < amounts[1] < amounts[2]
        decreasing_streak = amounts[0] > amounts[1] > amounts[2]
        if increasing_streak:
            insights.append({"type": "expense_streak", "severity": "medium", "message": "Recorded expenses increased for three consecutive months.", "supporting_values": amounts})
        elif decreasing_streak:
            insights.append({"type": "expense_streak", "severity": "positive", "message": "Recorded expenses decreased for three consecutive months.", "supporting_values": amounts})

    category_trends = [
        {
            "category": row["category"],
            "status": row["trend"],
            "current_amount": row["current_amount"],
            "previous_amount": row["previous_amount"],
            "change_percent": row["percentage_change"],
        }
        for row in overview["spending"]["category_trends"]
        if row["trend"] in {"increasing", "decreasing", "stable"}
    ]
    for row in category_trends:
        insights.append({
            "type": "category_trend",
            "severity": "medium" if row["status"] == "increasing" else "positive" if row["status"] == "decreasing" else "low",
            "message": f"{row['category']} spending is {row['status']} compared with the previous observed month.",
            "supporting_values": row,
        })

    income_months = [row for row in monthly if row["total_income"] > 0 and row["savings_rate"] is not None]
    savings_rate_trend = {"status": "insufficient_data", "current_percent": None, "previous_percent": None, "change_percent": None}
    if len(income_months) >= 2 and _consecutive(income_months[-2], income_months[-1]):
        before, current = income_months[-2]["savings_rate"], income_months[-1]["savings_rate"]
        change = (current - before).quantize(Decimal("0.01"))
        status = "improving" if change > 0 else "declining" if change < 0 else "stable"
        savings_rate_trend = {"status": status, "current_percent": current, "previous_percent": before, "change_percent": change}
        if status in {"improving", "declining"}:
            insights.append({"type": "savings_rate_trend", "severity": "positive" if status == "improving" else "high", "message": f"Your recorded savings rate is {status} month over month.", "supporting_values": savings_rate_trend})

    contributions = snapshot["goal_contributions"]
    active_goals = [goal for goal in snapshot["goals"] if goal.status == "active"]
    today = date.today()
    goal_start_dates = [start for goal in active_goals if (start := _goal_start_date(goal)) is not None]
    oldest_goal_start = min(goal_start_dates) if goal_start_dates else today
    observed_goal_months = min(6, max(1, (today.year - oldest_goal_start.year) * 12 + today.month - oldest_goal_start.month + 1))
    goal_ids = {goal.id for goal in active_goals}
    last_six_months = {_month_key(today, offset) for offset in range(observed_goal_months)}
    contribution_months = {
        (row.contributed_at.year, row.contributed_at.month)
        for row in contributions
        if row.goal_id in goal_ids
        if getattr(row, "change_type", "contribution") == "contribution"
        and row.amount > 0
        if (row.contributed_at.year, row.contributed_at.month) in last_six_months
    }
    goal_consistency = Decimal(len(contribution_months)) / Decimal(observed_goal_months) * Decimal("100") if active_goals else None

    behavior = _classify(profile, len(monthly), goal_consistency, len(contribution_months))
    recurring = [
        {
            "category": row["category"],
            "average_amount": row["average_amount"],
            "frequency": row["frequency"],
            "occurrences": row["occurrences"],
            "confidence": row["confidence"],
        }
        for row in overview["recurring"][:8]
    ]
    anomalies = [
        {
            "category": row["category"],
            "period": row["period"],
            "current_amount": row["current_amount"],
            "historical_average": row["historical_average"],
            "explanation": row["explanation"],
        }
        for row in overview["anomalies"][:8]
    ]
    for item in anomalies:
        insights.append({"type": "unusual_spending", "severity": "medium", "message": item["explanation"], "supporting_values": item})

    return {
        "available": bool(monthly),
        "observed_months": len(monthly),
        "monthly_expense_trend": monthly_trend,
        "three_month_expense_pattern": "increasing" if increasing_streak else "decreasing" if decreasing_streak else "not_detected",
        "category_trends": category_trends,
        "savings_rate_trend": savings_rate_trend,
        "goal_contribution_consistency_percent": goal_consistency,
        "goal_contribution_basis_months": observed_goal_months if active_goals else 0,
        "recurring_expenses": recurring,
        "unusual_spending": anomalies,
        "seasonality": _seasonality(snapshot["expenses"], monthly),
        "behavioral_classification": behavior,
        "insights": insights,
        "insufficient_data": [] if monthly else ["Not enough historical financial data is available to analyze spending behavior yet."],
    }


def _month_key(today: date, offset: int) -> tuple[int, int]:
    value = today.year * 12 + today.month - 1 - offset
    return value // 12, value % 12 + 1


def _classify(profile: dict, month_count: int, goal_consistency, contribution_month_count: int) -> dict:
    if month_count < 3:
        return {"label": "Insufficient data", "basis": "At least three observed transaction months are needed for behavior classification."}
    volatility = profile["spending_volatility_percent"]
    income_variation = profile["income_variation_percent"]
    if (volatility is not None and volatility >= 40) or (income_variation is not None and income_variation >= 45):
        return {"label": "Irregular Spender", "basis": "Observed monthly spending volatility or income variation is high."}
    if profile["discretionary_expense_ratio_percent"] is not None and profile["discretionary_expense_ratio_percent"] >= 40:
        return {"label": "High Discretionary Spender", "basis": "At least 40% of average recorded expenses are classified as non-essential."}
    if profile["active_goal_count"] and contribution_month_count >= 3 and goal_consistency is not None and profile["average_savings_rate_percent"] is not None and profile["average_savings_rate_percent"] > 0:
        return {"label": "Goal-Oriented", "basis": "An active goal, positive recorded savings, and contributions in at least three of the last six calendar months were observed."}
    if profile["average_savings_rate_percent"] is not None and profile["average_savings_rate_percent"] >= 20 and profile["savings_consistency_percent"] is not None and profile["savings_consistency_percent"] >= 70:
        return {"label": "Saver", "basis": "Average recorded savings rate is at least 20% and positive-savings months occur consistently."}
    return {"label": "Balanced", "basis": "The recorded history does not meet the measured thresholds for the other behavior groups."}


def _seasonality(expenses: list, monthly: list) -> dict:
    if len(monthly) < 24:
        return {"available": False, "reason": "Seasonality needs at least 24 observed transaction months."}
    observed_month_totals: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in expenses:
        if row.date <= date.today():
            key = (row.date.year, row.date.month)
            observed_month_totals[key] += row.amount
    totals_by_calendar_month: dict[int, list[Decimal]] = defaultdict(list)
    for (_year, calendar_month), amount in observed_month_totals.items():
        totals_by_calendar_month[calendar_month].append(amount)
    per_month = {
        number: sum(values, Decimal("0")) / Decimal(len(values))
        for number, values in totals_by_calendar_month.items()
        if len(values) >= 2
    }
    if not per_month:
        return {"available": False, "reason": "There are not enough repeated calendar-month observations to compare seasonality."}
    peak = max(per_month.items(), key=lambda item: item[1])
    average = sum(per_month.values(), Decimal("0")) / Decimal(len(per_month))
    return {
        "available": True,
        "peak_calendar_month": month_name[peak[0]],
        "observed_total": peak[1],
        "comparison_average": average,
        "basis_months": len(per_month),
        "reason": "Average calendar-month expense totals are compared only where at least two years of observations exist.",
    }
