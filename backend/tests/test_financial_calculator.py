"""Unit tests for the Phase 2 financial calculations."""

from decimal import Decimal
from types import SimpleNamespace
import unittest

from app.services.financial_calculator import calculate_financial_summary
from app.services.financial_health import health_indicators


class FinancialCalculatorTests(unittest.TestCase):
    def test_positive_surplus_and_savings_rate(self) -> None:
        incomes = [SimpleNamespace(amount=Decimal("50000.00"))]
        expenses = [
            SimpleNamespace(amount=Decimal("30000.00"), expense_type="Essential")
        ]

        summary = calculate_financial_summary(incomes, expenses)
        summary.update(health_indicators(summary))

        self.assertEqual(summary["surplus"], Decimal("20000.00"))
        self.assertEqual(summary["savings_rate"], Decimal("40.00"))
        self.assertEqual(summary["financial_status"], "Healthy")

    def test_expenses_over_income_are_a_deficit(self) -> None:
        incomes = [SimpleNamespace(amount=Decimal("50000.00"))]
        expenses = [
            SimpleNamespace(amount=Decimal("60000.00"), expense_type="Essential")
        ]

        summary = calculate_financial_summary(incomes, expenses)
        summary.update(health_indicators(summary))

        self.assertEqual(summary["surplus"], Decimal("-10000.00"))
        self.assertEqual(summary["deficit"], Decimal("10000.00"))
        self.assertEqual(summary["financial_status"], "Deficit")

    def test_zero_income_does_not_divide_by_zero(self) -> None:
        summary = calculate_financial_summary([], [])
        summary.update(health_indicators(summary))

        self.assertEqual(summary["savings_rate"], Decimal("0.00"))
        self.assertEqual(summary["expense_ratio"], Decimal("0.00"))
        self.assertEqual(summary["essential_expense_ratio"], Decimal("0.00"))
        self.assertEqual(summary["financial_status"], "Needs Attention")


if __name__ == "__main__":
    unittest.main()
