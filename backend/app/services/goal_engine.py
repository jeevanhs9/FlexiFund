"""Explainable goal progress and surplus-aware allocation strategy."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal, ROUND_CEILING


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _money(value: Decimal | int | float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value).quantize(Decimal("0.01"))


def _months_remaining(target: date, today: date) -> int:
    return max(1, (target.year - today.year) * 12 + target.month - today.month)


def _plus_months(start: date, months: int) -> date:
    month_index = start.year * 12 + start.month - 1 + months
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def build_goal_plan(snapshot: dict, profile: dict, *, today: date | None = None) -> dict:
    """Calculate goal math and allocate observed positive surplus by priority/deadline."""
    today = today or date.today()
    average_surplus = profile.get("average_monthly_surplus")
    average_income = profile.get("average_monthly_income")
    capacity = max(Decimal("0"), average_surplus) if average_surplus is not None else None
    summaries = []

    for goal in snapshot["goals"]:
        remaining = max(Decimal("0"), goal.target_amount - goal.current_amount)
        progress = min(Decimal("100"), goal.current_amount / goal.target_amount * Decimal("100"))
        months = _months_remaining(goal.target_date, today) if remaining else 0
        required = (remaining / Decimal(months)).quantize(Decimal("0.01")) if months else Decimal("0.00")
        required_rate = (
            (required / average_income * Decimal("100")).quantize(Decimal("0.01"))
            if average_income is not None and average_income > 0
            else None
        )
        completion_date = None
        if remaining == 0:
            feasibility = "completed"
            completion_date = today
        elif goal.status == "paused":
            feasibility = "paused"
        elif capacity is None:
            feasibility = "insufficient_data"
        elif capacity <= 0:
            feasibility = "not_feasible_with_observed_surplus"
        else:
            needed_months = int((remaining / capacity).to_integral_value(rounding=ROUND_CEILING))
            completion_date = _plus_months(today, needed_months)
            feasibility = "on_track_with_observed_surplus" if required <= capacity else "stretch_goal"
        summaries.append(
            {
                "id": goal.id,
                "name": goal.name,
                "target_amount": _money(goal.target_amount),
                "current_amount": _money(goal.current_amount),
                "remaining_amount": _money(remaining),
                "progress_percent": progress.quantize(Decimal("0.01")),
                "target_date": goal.target_date,
                "months_remaining": months,
                "required_monthly_savings": _money(required),
                "required_savings_rate_percent": required_rate,
                "projected_completion_date": completion_date,
                "feasibility": feasibility,
                "priority": goal.priority,
                "category": goal.category,
                "status": goal.status,
            }
        )

    active_by_id = {row["id"]: row for row in summaries if row["status"] == "active" and row["remaining_amount"] > 0}
    prioritized = sorted(
        active_by_id.values(),
        key=lambda row: (PRIORITY_ORDER.get(row["priority"], 9), row["target_date"], row["id"]),
    )
    remaining_capacity = capacity
    allocations = []
    for rank, goal in enumerate(prioritized, start=1):
        requirement = goal["required_monthly_savings"]
        allocated = min(requirement, remaining_capacity) if remaining_capacity is not None else None
        shortfall = requirement - allocated if allocated is not None else None
        if allocated is not None:
            remaining_capacity -= allocated
        goal["recommended_monthly_allocation"] = _money(allocated)
        goal["allocation_shortfall"] = _money(shortfall)
        goal["allocation_rank"] = rank
        if rank == 1:
            reason = f"{goal['priority'].title()} priority and the earliest deadline among goals at this priority."
        else:
            reason = f"Ranked after higher-priority or earlier-due active goals; allocation uses remaining observed surplus."
        allocations.append(
            {
                "goal_id": goal["id"],
                "goal_name": goal["name"],
                "priority": goal["priority"],
                "rank": rank,
                "required_monthly_savings": goal["required_monthly_savings"],
                "recommended_monthly_allocation": goal["recommended_monthly_allocation"],
                "allocation_shortfall": goal["allocation_shortfall"],
                "reason": reason,
            }
        )

    risk = snapshot["overview"]["risk"]
    emergency_fund = snapshot["overview"]["emergency_fund"]
    return {
        "available": bool(snapshot["goals"]),
        "goals": summaries,
        "optimization": {
            "available": capacity is not None and bool(prioritized),
            "observed_monthly_contribution_capacity": _money(capacity),
            "basis_month_count": profile.get("cash_flow_month_count", 0),
            "allocated_monthly_total": _money(capacity - remaining_capacity) if capacity is not None else None,
            "unallocated_monthly_capacity": _money(remaining_capacity),
            "risk_band": risk["band"],
            "emergency_fund_balance_configured": emergency_fund["balance_configured"],
            "allocations": allocations,
            "method": "Active goals are ordered by priority, then target date. Each receives up to its calculated monthly requirement from observed positive average surplus. This is a planning estimate, not a guarantee.",
        },
        "insufficient_data": [] if snapshot["goals"] and capacity is not None else (
            ["Create an active goal to see progress and allocation strategy."] if not snapshot["goals"] else
            ["Record income and expenses in the same months to estimate contribution capacity."]
        ),
    }
