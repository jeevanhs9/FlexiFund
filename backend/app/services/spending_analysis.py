"""Explainable category mix, change and overspending analysis."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import mean, pstdev

from app.services.financial_calculator import calculate_percentage

MONEY_THRESHOLD = Decimal("250")


def analyze_spending(transactions: list, selected: list, monthly: list) -> dict:
    expenses = [row for row in selected if row.kind == "expense"]
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in expenses:
        totals[row.category or "Uncategorized"] += row.amount
    total_expenses = sum(totals.values(), Decimal("0"))
    categories = [
        {
            "category": name,
            "amount": amount.quantize(Decimal("0.01")),
            "percentage": calculate_percentage(amount, total_expenses),
            "transaction_count": sum(1 for row in expenses if (row.category or "Uncategorized") == name),
        }
        for name, amount in sorted(totals.items(), key=lambda item: (-item[1], item[0].casefold()))
    ]

    observed_months = sorted({(row.date.year, row.date.month) for row in transactions})
    if selected:
        selected_month = max((row.date.year, row.date.month) for row in selected)
    elif observed_months:
        selected_month = observed_months[-1]
    else:
        selected_month = None
    month_category: dict[tuple[int, int, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in transactions:
        if row.kind != "expense":
            continue
        key = (row.date.year, row.date.month)
        month_category[(*key, row.category or "Uncategorized")] += row.amount

    trends = []
    overspending = []
    if selected_month:
        current_index = observed_months.index(selected_month) if selected_month in observed_months else -1
        previous_month = observed_months[current_index - 1] if current_index > 0 else None
        if previous_month:
            previous_expected = (selected_month[0] - 1, 12) if selected_month[1] == 1 else (selected_month[0], selected_month[1] - 1)
            if previous_month != previous_expected:
                previous_month = None
        categories_in_history = sorted({key[2] for key in month_category})
        for category in categories_in_history:
            current_amount = month_category[(selected_month[0], selected_month[1], category)]
            previous_amount = month_category[(*previous_month, category)] if previous_month else Decimal("0")
            historical_months = [key for key in observed_months if key < selected_month]
            baseline_keys = historical_months[-3:]
            baseline = [month_category[(*key, category)] for key in baseline_keys]
            change = None
            if previous_month and previous_amount > 0:
                change = ((current_amount - previous_amount) / previous_amount * Decimal("100")).quantize(Decimal("0.01"))
            if previous_month:
                delta = current_amount - previous_amount
                if abs(delta) >= MONEY_THRESHOLD and change is not None and abs(change) >= Decimal("10"):
                    trend = "increasing" if delta > 0 else "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_history"
            trends.append(
                {
                    "category": category,
                    "current_amount": current_amount.quantize(Decimal("0.01")),
                    "previous_amount": previous_amount.quantize(Decimal("0.01")) if previous_month else None,
                    "historical_average": (sum(baseline, Decimal("0")) / len(baseline)).quantize(Decimal("0.01")) if baseline else None,
                    "percentage_change": change,
                    "trend": trend,
                }
            )

            if len(baseline) >= 3 and current_amount > 0 and any(value > 0 for value in baseline):
                average = Decimal(str(mean(float(value) for value in baseline)))
                deviation = Decimal(str(pstdev(float(value) for value in baseline)))
                threshold = max(average * Decimal("1.25"), average + deviation * Decimal("1.5"))
                if current_amount - average >= MONEY_THRESHOLD and current_amount > threshold:
                    increase = ((current_amount - average) / average * Decimal("100")).quantize(Decimal("0.01")) if average else None
                    overspending.append(
                        {
                            "category": category,
                            "status": "overspending",
                            "current_amount": current_amount.quantize(Decimal("0.01")),
                            "historical_average": average.quantize(Decimal("0.01")),
                            "increase_percentage": increase,
                            "severity": "high" if increase is not None and increase >= 75 else "moderate",
                            "threshold": threshold.quantize(Decimal("0.01")),
                            "baseline_months": len(baseline),
                        }
                    )

    average_monthly_spending = (
        sum((item["total_expenses"] for item in monthly), Decimal("0")) / len(monthly)
        if monthly else None
    )
    monthly_expense_values = [float(item["total_expenses"]) for item in monthly]
    volatility = None
    if len(monthly_expense_values) >= 2 and mean(monthly_expense_values) != 0:
        volatility = Decimal(str(pstdev(monthly_expense_values) / mean(monthly_expense_values) * 100)).quantize(Decimal("0.01"))
    largest = sorted(expenses, key=lambda row: (-row.amount, row.date, row.id or 0))[:5]

    return {
        "total_expenses": total_expenses.quantize(Decimal("0.01")),
        "categories": categories,
        "top_category": categories[0] if categories else None,
        "lowest_category": categories[-1] if categories else None,
        "category_trends": sorted(trends, key=lambda item: item["category"].casefold()),
        "overspending": sorted(overspending, key=lambda item: (-float(item["increase_percentage"] or 0), item["category"])),
        "average_monthly_spending": average_monthly_spending.quantize(Decimal("0.01")) if average_monthly_spending is not None else None,
        "spending_volatility_percent": volatility,
        "spending_concentration_percent": categories[0]["percentage"] if categories else None,
        "largest_transactions": [
            {
                "id": row.id,
                "date": row.date,
                "category": row.category or "Uncategorized",
                "amount": row.amount,
                "description": row.description,
            }
            for row in largest
        ],
        "selected_month": {"year": selected_month[0], "month": selected_month[1]} if selected_month else None,
    }
