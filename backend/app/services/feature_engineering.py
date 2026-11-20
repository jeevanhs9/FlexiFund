"""Features derived from observed financial transactions only."""

from __future__ import annotations

from decimal import Decimal

from app.services.financial_engine import monthly_financials


def _growth(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None
    return ((current - previous) / abs(previous) * Decimal("100")).quantize(Decimal("0.01"))


def _consecutive(left: dict, right: dict) -> bool:
    expected_month = left["month_number"] % 12 + 1
    expected_year = left["year"] + (1 if left["month_number"] == 12 else 0)
    return (right["year"], right["month_number"]) == (expected_year, expected_month)


def engineer_features(transactions: list) -> dict:
    """Build monthly ratios, cash flow and trend features from actual rows."""
    months = monthly_financials(transactions)
    expenses_by_month: dict[tuple[int, int], list] = {}
    for row in transactions:
        expenses_by_month.setdefault((row.date.year, row.date.month), []).append(row)

    features = []
    for index, item in enumerate(months):
        rows = expenses_by_month[(item["year"], item["month_number"])]
        transaction_count = len(rows)
        expense_transaction_count = sum(row.kind == "expense" for row in rows)
        average_transaction = (
            sum((row.amount for row in rows), Decimal("0")) / transaction_count
            if transaction_count else Decimal("0")
        )
        previous = months[index - 1] if index > 0 and _consecutive(months[index - 1], item) else None
        features.append(
            {
                **item,
                "monthly_income": item["total_income"],
                "monthly_expenses": item["total_expenses"],
                "monthly_savings": item["surplus"],
                "cash_flow": item["surplus"],
                "savings_rate": item["savings_rate"] if item["total_income"] else None,
                "expense_ratio": item["expense_ratio"] if item["total_income"] else None,
                "essential_expenses": item["essential_expenses"],
                "non_essential_expenses": item["non_essential_expenses"],
                "essential_expense_ratio": item["essential_expense_ratio"],
                "non_essential_expense_ratio": item["non_essential_expense_ratio"],
                "transaction_count": transaction_count,
                # A zero total is not treated as an observed expense month by
                # the predictive model. This prevents income-only months from
                # becoming invented zero-expense labels.
                "expense_transaction_count": expense_transaction_count,
                "average_transaction": average_transaction.quantize(Decimal("0.01")),
                "income_growth": _growth(item["total_income"], previous["total_income"]) if previous else None,
                "expense_growth": _growth(item["total_expenses"], previous["total_expenses"]) if previous else None,
                "savings_growth": _growth(item["surplus"], previous["surplus"]) if previous else None,
                "cash_flow_change": (item["surplus"] - previous["surplus"]) if previous else None,
            }
        )
    return {"monthly_history": features, "history_month_count": len(features)}
