"""Explainable unusual-spending checks; results are not fraud findings."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import mean, pstdev


def detect_anomalies(transactions: list, selected: list) -> list[dict]:
    monthly_by_category: dict[tuple[int, int, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in transactions:
        if row.kind == "expense":
            monthly_by_category[(row.date.year, row.date.month, row.category or "Uncategorized")] += row.amount

    selected_months = sorted({(row.date.year, row.date.month) for row in selected})
    if not selected_months:
        return []
    target = selected_months[-1]
    categories = sorted({key[2] for key in monthly_by_category})
    anomalies = []
    for category in categories:
        history = [
            value for (year, month, cat), value in monthly_by_category.items()
            if cat == category and (year, month) < target
        ]
        current = monthly_by_category[(target[0], target[1], category)]
        if len(history) < 3 or current <= 0:
            continue
        average = Decimal(str(mean(float(value) for value in history)))
        deviation = Decimal(str(pstdev(float(value) for value in history)))
        threshold = max(average * Decimal("1.25"), average + deviation * Decimal("1.5"))
        if current - average >= Decimal("250") and current > threshold:
            percent = ((current - average) / average * Decimal("100")).quantize(Decimal("0.01")) if average else None
            anomalies.append(
                {
                    "type": "category_spending_spike",
                    "label": "Unusual Spending",
                    "category": category,
                    "period": f"{target[0]:04d}-{target[1]:02d}",
                    "current_amount": current.quantize(Decimal("0.01")),
                    "historical_average": average.quantize(Decimal("0.01")),
                    "threshold": threshold.quantize(Decimal("0.01")),
                    "increase_percentage": percent,
                    "method": "historical_mean_plus_1_5_standard_deviations_and_25_percent_floor",
                    "explanation": f"{category} spending exceeded its prior {len(history)} observed monthly values and the configured statistical threshold.",
                }
            )

    prior_by_category: dict[str, list] = defaultdict(list)
    for row in transactions:
        if row.kind == "expense" and (row.date.year, row.date.month) < target:
            prior_by_category[row.category or "Uncategorized"].append(row)
    month_start = date(target[0], target[1], 1)
    target_transactions = [
        row for row in selected if (row.date.year, row.date.month) == target
    ]
    for row in target_transactions:
        if row.kind != "expense":
            continue
        peer_rows = [
            peer for peer in prior_by_category[row.category or "Uncategorized"]
            if peer.date < month_start
        ]
        if len(peer_rows) < 5:
            continue
        peers = [peer.amount for peer in peer_rows]
        values = sorted(float(value) for value in peers)
        median = Decimal(str(values[len(values) // 2]))
        upper = Decimal(str(values[min(len(values) - 1, int(0.75 * (len(values) - 1)))]))
        lower = Decimal(str(values[int(0.25 * (len(values) - 1))]))
        threshold = max(upper + Decimal("1.5") * (upper - lower), median * 2, median + Decimal("1000"))
        if row.amount > threshold:
            anomalies.append(
                {
                    "type": "unusually_large_transaction",
                    "label": "Unusual Spending",
                    "category": row.category or "Uncategorized",
                    "period": row.date.isoformat(),
                    "current_amount": row.amount,
                    "historical_average": (sum(peers, Decimal("0")) / len(peers)).quantize(Decimal("0.01")),
                    "threshold": threshold.quantize(Decimal("0.01")),
                    "transaction_id": row.id,
                    "method": "category_peer_iqr_and_median_floor",
                    "explanation": f"This transaction is unusually large compared with {len(peers)} previous transactions in the same category.",
                }
            )
    return anomalies
