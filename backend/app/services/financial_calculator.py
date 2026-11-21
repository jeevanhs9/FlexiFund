"""Pure financial calculations using Decimal arithmetic."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol, TypeAlias

MoneyValue: TypeAlias = Decimal | int | float
CENT = Decimal("0.01")
ZERO = Decimal("0.00")
PERCENT = Decimal("100")


class AmountRecord(Protocol):
    amount: Decimal


class ExpenseRecord(AmountRecord, Protocol):
    expense_type: str


def _amount(value: AmountRecord | MoneyValue) -> Decimal:
    raw_amount = value.amount if hasattr(value, "amount") else value
    return Decimal(str(raw_amount))


def _sum_amounts(values: list[AmountRecord | MoneyValue]) -> Decimal:
    return sum((_amount(value) for value in values), start=ZERO).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def _percentage(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return ZERO
    return ((numerator / denominator) * PERCENT).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def calculate_percentage(numerator: Decimal, denominator: Decimal) -> Decimal:
    """Return a safe, rounded percentage for financial analysis modules."""
    return _percentage(numerator, denominator)


def calculate_total_income(income_records: list[AmountRecord]) -> Decimal:
    """Return the sum of income record amounts."""
    return _sum_amounts(list(income_records))


def calculate_total_expenses(expense_records: list[ExpenseRecord]) -> Decimal:
    """Return the sum of expense record amounts."""
    return _sum_amounts(list(expense_records))


def calculate_monthly_surplus(total_income: Decimal, total_expenses: Decimal) -> Decimal:
    """Return income less expenses, preserving a negative deficit value."""
    return (total_income - total_expenses).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_work_adjusted_net_income(
    total_income: Decimal, work_related_expenses: Decimal
) -> Decimal:
    """Return income after the imported expenses marked as work-related.

    Work-related expenses remain part of total expenses, so the existing
    surplus calculation already deducts them. This supplemental value makes
    the work-cost impact explicit without introducing a disconnected engine.
    """
    return (total_income - work_related_expenses).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_savings_rate(total_income: Decimal, surplus: Decimal) -> Decimal:
    """Return surplus as a percentage of income, or zero when income is zero."""
    return _percentage(surplus, total_income)


def calculate_expense_ratio(total_income: Decimal, total_expenses: Decimal) -> Decimal:
    """Return expenses as a percentage of income, or zero when income is zero."""
    return _percentage(total_expenses, total_income)


def calculate_essential_expenses(expense_records: list[ExpenseRecord]) -> Decimal:
    """Sum expenses classified as essential."""
    return _sum_amounts(
        [record for record in expense_records if record.expense_type == "Essential"]
    )


def calculate_non_essential_expenses(expense_records: list[ExpenseRecord]) -> Decimal:
    """Sum expenses classified as non-essential."""
    return _sum_amounts(
        [record for record in expense_records if record.expense_type == "Non-Essential"]
    )


def calculate_essential_expense_ratio(
    essential_expenses: Decimal, total_expenses: Decimal
) -> Decimal:
    """Return essential expenses as a percentage of all expenses."""
    return _percentage(essential_expenses, total_expenses)


def calculate_financial_summary(
    income_records: list[AmountRecord], expense_records: list[ExpenseRecord]
) -> dict[str, Decimal]:
    """Calculate all summary values from already-filtered records."""
    total_income = calculate_total_income(income_records)
    total_expenses = calculate_total_expenses(expense_records)
    surplus = calculate_monthly_surplus(total_income, total_expenses)
    essential = calculate_essential_expenses(expense_records)
    non_essential = calculate_non_essential_expenses(expense_records)

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "surplus": surplus,
        "savings_rate": calculate_savings_rate(total_income, surplus),
        "expense_ratio": calculate_expense_ratio(total_income, total_expenses),
        "essential_expenses": essential,
        "non_essential_expenses": non_essential,
        "essential_expense_ratio": calculate_essential_expense_ratio(
            essential, total_expenses
        ),
        "non_essential_expense_ratio": _percentage(non_essential, total_expenses),
    }
