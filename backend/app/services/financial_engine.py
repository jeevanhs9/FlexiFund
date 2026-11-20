"""Financial-engine adapters that reuse the project's Decimal calculator."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Iterable

from app.services.financial_calculator import calculate_financial_summary


def calculate_summary(transactions: Iterable) -> dict[str, Decimal]:
    """Apply the central calculator to normalized transaction records."""
    rows = list(transactions)
    incomes = [SimpleNamespace(amount=row.amount) for row in rows if row.kind == "income"]
    expenses = [
        SimpleNamespace(amount=row.amount, expense_type=row.expense_type)
        for row in rows
        if row.kind == "expense"
    ]
    return calculate_financial_summary(incomes, expenses)


def monthly_financials(transactions: Iterable) -> list[dict]:
    """Return central-engine metrics for months containing actual transactions."""
    grouped: dict[tuple[int, int], list] = defaultdict(list)
    for row in transactions:
        grouped[(row.date.year, row.date.month)].append(row)
    result = []
    for (year, month), rows in sorted(grouped.items()):
        summary = calculate_summary(rows)
        result.append({"year": year, "month_number": month, "month": date(year, month, 1).strftime("%B"), **summary})
    return result
