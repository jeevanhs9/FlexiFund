"""Read-only, monthly what-if projections that never mutate stored records."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_CEILING


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _monthly_recurring_capacity(snapshot: dict, category: str) -> Decimal:
    total = Decimal("0")
    for recurring in snapshot["overview"]["recurring"]:
        if recurring["category"] != category:
            continue
        amount = recurring["average_amount"]
        frequency = recurring["frequency"]
        if frequency == "monthly":
            total += amount
        elif frequency == "weekly":
            total += amount * Decimal("4.33")
    return total.quantize(Decimal("0.01"))


def simulate_scenario(snapshot: dict, changes: list, *, name: str | None = None) -> dict:
    summary = snapshot["overview"]["summary"]
    current_income = summary["total_income"]
    current_expenses = summary["total_expenses"]
    category_spending: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in snapshot["overview"]["spending"]["categories"]:
        category_spending[row["category"]] = row["amount"]
    proposed_income = Decimal(current_income)
    proposed_categories = dict(category_spending)
    planned_savings_allocation = Decimal("0")
    planned_goal_contributions: dict[int, Decimal] = {}
    change_descriptions = []

    owned_goals = {goal.id: goal for goal in snapshot["goals"]}
    goal_contribution_totals: dict[tuple[int, int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    for contribution in snapshot["goal_contributions"]:
        if contribution.change_type == "contribution":
            key = (contribution.goal_id, contribution.contributed_at.year, contribution.contributed_at.month)
            goal_contribution_totals[key] += contribution.amount
    today = date.today()
    current_goal_completion = []
    for goal in snapshot["goals"]:
        created = getattr(goal, "created_at", None)
        goal_start = created.date() if isinstance(created, datetime) else created if isinstance(created, date) else today
        basis_months = min(6, max(1, (today.year - goal_start.year) * 12 + today.month - goal_start.month + 1))
        goal_month_keys = []
        for offset in range(basis_months):
            index = today.year * 12 + today.month - 1 - offset
            goal_month_keys.append((index // 12, index % 12 + 1))
        recent_total = sum(
            (goal_contribution_totals.get((goal.id, year, month), Decimal("0")) for year, month in goal_month_keys),
            Decimal("0"),
        )
        observed_average = (recent_total / Decimal(basis_months)).quantize(Decimal("0.01"))
        remaining = max(Decimal("0"), goal.target_amount - goal.current_amount)
        projected_months = int((remaining / observed_average).to_integral_value(rounding=ROUND_CEILING)) if remaining > 0 and observed_average > 0 else None
        current_goal_completion.append(
            {
                "goal_id": goal.id,
                "goal_name": goal.name,
                "progress_percent": _money(min(Decimal("100"), goal.current_amount / goal.target_amount * Decimal("100"))),
                "remaining_amount": _money(remaining),
                "recorded_average_monthly_contribution": observed_average if recent_total > 0 else None,
                "contribution_basis_months": basis_months,
                "projected_months_to_target": projected_months,
                "status": "projected_from_recorded_contributions" if projected_months is not None else "insufficient_contribution_history",
            }
        )
    for change in changes:
        kind = change.change_type
        amount = Decimal(change.amount)
        category = change.category
        if kind == "reduce_expense_category":
            current = proposed_categories.get(category, Decimal("0"))
            if current <= 0 or amount > current:
                raise ValueError(f"The proposed reduction for {category} exceeds its recorded current-month spending.")
            proposed_categories[category] = current - amount
            change_descriptions.append({"type": kind, "category": category, "amount": _money(amount)})
        elif kind == "increase_income":
            proposed_income += amount
            change_descriptions.append({"type": kind, "amount": _money(amount)})
        elif kind == "decrease_recurring_expense":
            recurring_capacity = _monthly_recurring_capacity(snapshot, category)
            current = proposed_categories.get(category, Decimal("0"))
            if recurring_capacity <= 0 or current <= 0 or amount > min(recurring_capacity, current):
                raise ValueError(f"The proposed recurring reduction for {category} exceeds detected recurring or current recorded spending.")
            proposed_categories[category] = current - amount
            change_descriptions.append({"type": kind, "category": category, "amount": _money(amount), "detected_monthly_recurring_amount": recurring_capacity})
        elif kind == "add_recurring_expense":
            proposed_categories[category] = proposed_categories.get(category, Decimal("0")) + amount
            change_descriptions.append({"type": kind, "category": category, "amount": _money(amount)})
        elif kind == "change_budget":
            previous = proposed_categories.get(category, Decimal("0"))
            proposed_categories[category] = amount
            change_descriptions.append({"type": kind, "category": category, "previous_spending": _money(previous), "new_budget": _money(amount)})
        elif kind == "increase_savings":
            planned_savings_allocation += amount
            change_descriptions.append({"type": kind, "monthly_savings_allocation": _money(amount)})
        elif kind == "change_goal_contribution":
            if change.goal_id not in owned_goals:
                raise LookupError("The requested financial goal was not found.")
            if owned_goals[change.goal_id].status != "active":
                raise ValueError("Monthly contributions can only be projected for an active goal.")
            planned_goal_contributions[change.goal_id] = amount
            change_descriptions.append({"type": kind, "goal_id": change.goal_id, "monthly_contribution": _money(amount)})

    proposed_expenses = sum(proposed_categories.values(), Decimal("0"))
    proposed_surplus = proposed_income - proposed_expenses
    current_surplus = Decimal(current_income) - Decimal(current_expenses)
    if planned_savings_allocation + sum(planned_goal_contributions.values(), Decimal("0")) > max(Decimal("0"), proposed_surplus):
        raise ValueError("Planned savings contributions cannot exceed the projected positive monthly surplus.")

    current_plan = {
        "label": "CURRENT PLAN · ACTUAL RECORDS",
        "income": _money(Decimal(current_income)),
        "expenses": _money(Decimal(current_expenses)),
        "surplus": _money(current_surplus),
        "savings_rate_percent": _money(current_surplus / Decimal(current_income) * Decimal("100")) if current_income else None,
        "category_spending": {key: _money(value) for key, value in sorted(category_spending.items())},
        "planned_monthly_savings_allocation": None,
        "goal_completion": current_goal_completion,
        "projected_annual_surplus": _money(current_surplus * Decimal("12")),
        "projected_annual_savings": _money(max(Decimal("0"), current_surplus) * Decimal("12")),
        "financial_health": {"score": snapshot["overview"]["risk"]["score"], "band": snapshot["overview"]["risk"]["band"], "label": "Phase 5 score from recorded history"},
    }

    completion = []
    for goal_id, monthly_amount in planned_goal_contributions.items():
        goal = owned_goals[goal_id]
        remaining = max(Decimal("0"), goal.target_amount - goal.current_amount)
        projected_months = (
            int((remaining / monthly_amount).to_integral_value(rounding=ROUND_CEILING))
            if monthly_amount > 0 and remaining > 0 else 0
        )
        completion.append(
            {
                "goal_id": goal_id,
                "goal_name": goal.name,
                "remaining_amount": _money(remaining),
                "scenario_monthly_contribution": _money(monthly_amount),
                "projected_months_to_target": projected_months if monthly_amount > 0 else None,
                "status": "projected" if monthly_amount > 0 else "no_contribution",
            }
        )

    proposed_goal_completion = []
    for actual in current_goal_completion:
        proposed_amount = planned_goal_contributions.get(actual["goal_id"])
        if proposed_amount is None:
            proposed_goal_completion.append(actual)
            continue
        proposed = next(row for row in completion if row["goal_id"] == actual["goal_id"])
        proposed_goal_completion.append({**actual, **proposed})

    proposed_plan = {
        "label": "PROPOSED PLAN · PROJECTED SCENARIO",
        "income": _money(proposed_income),
        "expenses": _money(proposed_expenses),
        "surplus": _money(proposed_surplus),
        "savings_rate_percent": _money(proposed_surplus / proposed_income * Decimal("100")) if proposed_income else None,
        "category_spending": {key: _money(value) for key, value in sorted(proposed_categories.items())},
        "planned_monthly_savings_allocation": _money(planned_savings_allocation + sum(planned_goal_contributions.values(), Decimal("0"))),
        "goal_completion": proposed_goal_completion,
        "projected_annual_surplus": _money(proposed_surplus * Decimal("12")),
        "projected_annual_savings": _money(max(Decimal("0"), proposed_surplus) * Decimal("12")),
        "financial_health": {"score": None, "band": None, "label": "Not re-scored; the Phase 5 risk engine scores recorded history, not hypothetical plans."},
    }
    comparison = {
        "monthly_income_change": _money(proposed_income - Decimal(current_income)),
        "monthly_expense_change": _money(proposed_expenses - Decimal(current_expenses)),
        "monthly_surplus_change": _money(proposed_surplus - current_surplus),
        "annual_surplus_change_if_repeated": _money((proposed_surplus - current_surplus) * Decimal("12")),
        "annual_savings_change_if_repeated": _money(
            max(Decimal("0"), proposed_surplus) * Decimal("12")
            - max(Decimal("0"), current_surplus) * Decimal("12")
        ),
    }
    return {
        "name": name or "Proposed scenario",
        "status": "SCENARIO",
        "current_plan": current_plan,
        "proposed_plan": proposed_plan,
        "comparison": comparison,
        "changes": change_descriptions,
        "assumptions": [
            "Current values use the current calendar month’s recorded income and expenses; incomplete records may not represent a full month.",
            "The annual value assumes the monthly difference repeats for 12 months and is a projection, not a forecast or guarantee.",
            "Projected annual savings equal positive monthly surplus multiplied by 12; a projected deficit contributes zero savings.",
            "Savings allocations do not change income or expenses and are included only when they fit within projected positive surplus.",
            "Actual financial records are not modified by scenario calculations.",
        ],
    }
