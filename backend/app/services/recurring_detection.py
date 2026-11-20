"""Detect repeated expenses from transaction dates, categories and descriptions."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal


def _candidate(category: str, description: str, rows: list) -> dict | None:
    rows.sort(key=lambda row: row.date)
    if len(rows) < 3:
        return None
    selected = [rows[0]]
    for row in rows[1:]:
        previous = selected[-1]
        relative_amount_change = abs(row.amount - previous.amount) / max(row.amount, previous.amount)
        interval = (row.date - previous.date).days
        if relative_amount_change <= Decimal("0.20") and 6 <= interval <= 40:
            selected.append(row)
    if len(selected) < 3:
        return None
    intervals = [(right.date - left.date).days for left, right in zip(selected, selected[1:])]
    average_interval = sum(intervals) / len(intervals)
    frequency = "monthly" if 25 <= average_interval <= 35 else "weekly" if 6 <= average_interval <= 8 else "repeating"
    average_amount = (sum((row.amount for row in selected), Decimal("0")) / len(selected)).quantize(Decimal("0.01"))
    relative_spread = (max(row.amount for row in selected) - min(row.amount for row in selected)) / average_amount if average_amount else Decimal("1")
    confidence = "high" if len(selected) >= 4 and relative_spread <= Decimal("0.10") else "medium"
    return {
        "name": description.title() if description else category,
        "category": category,
        "average_amount": average_amount,
        "frequency": frequency,
        "confidence": confidence,
        "occurrences": len(selected),
        "last_date": selected[-1].date,
        "method": "repeated_category_description_interval_and_amount_similarity",
    }


def detect_recurring_expenses(transactions: list) -> list[dict]:
    expenses = [row for row in transactions if row.kind == "expense"]
    groups: dict[tuple[str, str], list] = defaultdict(list)
    category_groups: dict[str, list] = defaultdict(list)
    for row in expenses:
        description = (row.description or "").strip().casefold()
        # With no merchant text, same-category, similar-amount repeats remain detectable.
        key = (row.category or "Uncategorized", description)
        groups[key].append(row)
        category_groups[row.category or "Uncategorized"].append(row)

    recurring = []
    for (category, description), rows in groups.items():
        candidate = _candidate(category, description, rows)
        if candidate:
            recurring.append(candidate)

    recurring_categories = {item["category"] for item in recurring}
    for category, rows in category_groups.items():
        # If descriptions vary across periods, still allow category/amount/date evidence.
        if category not in recurring_categories:
            candidate = _candidate(category, "", rows)
            if candidate:
                candidate["method"] = "repeated_category_interval_and_amount_similarity"
                recurring.append(candidate)
    return sorted(recurring, key=lambda row: (row["category"].casefold(), row["name"].casefold()))
