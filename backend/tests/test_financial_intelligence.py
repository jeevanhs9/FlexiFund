"""Tests for the Phase 5 financial intelligence pipeline and API."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from werkzeug.security import generate_password_hash

from app import create_app
from app.database import create_tables, get_engine, session_scope
from app.models import Expense, Income, User
from app.services.forecasting_engine import forecast_cash_flow
from app.services.intelligence_service import build_intelligence_overview
from app.services.risk_engine import score_financial_risk


def income(user_id: int, amount: int, year: int, month: int, day: int = 10):
    return SimpleNamespace(
        id=None,
        user_id=user_id,
        amount=Decimal(amount),
        date=date(year, month, day),
        income_type="Salary",
        description="Salary",
    )


def expense(user_id: int, amount: int, year: int, month: int, *, category="Food", day=10):
    return SimpleNamespace(
        id=None,
        user_id=user_id,
        amount=Decimal(amount),
        date=date(year, month, day),
        category=category,
        expense_type="Non-Essential" if category == "Shopping" else "Essential",
        description=category,
    )


class FinancialIntelligenceTests(unittest.TestCase):
    def test_positive_cash_flow_and_risk_score_range(self):
        overview = build_intelligence_overview(
            [income(1, 50000, 2024, 4)],
            [expense(1, 30000, 2024, 4)],
            user_id=1,
            month=4,
            year=2024,
            as_of=date(2024, 4, 20),
        )
        self.assertEqual(overview["summary"]["surplus"], Decimal("20000.00"))
        self.assertIsNotNone(overview["risk"]["score"])
        self.assertGreaterEqual(overview["risk"]["score"], 0)
        self.assertLessEqual(overview["risk"]["score"], 100)

    def test_negative_cash_flow_creates_critical_factor(self):
        overview = build_intelligence_overview(
            [income(1, 30000, 2024, 4)],
            [expense(1, 35000, 2024, 4)],
            user_id=1,
            month=4,
            year=2024,
            as_of=date(2024, 4, 20),
        )
        self.assertEqual(overview["summary"]["surplus"], Decimal("-5000.00"))
        self.assertTrue(any(row["factor"] == "Negative Cash Flow" for row in overview["risk"]["risk_factors"]))
        self.assertTrue(any(row["priority"] == "CRITICAL" for row in overview["recommendations"]))
        positive = build_intelligence_overview(
            [income(1, 50000, 2024, 4)], [expense(1, 30000, 2024, 4)],
            user_id=1, month=4, year=2024, as_of=date(2024, 4, 20)
        )
        self.assertLess(overview["risk"]["score"], positive["risk"]["score"])

    def test_spending_spike_detected_against_three_observations(self):
        records = [
            expense(1, 4000, 2024, 1),
            expense(1, 4200, 2024, 2),
            expense(1, 4100, 2024, 3),
            expense(1, 9000, 2024, 4),
        ]
        overview = build_intelligence_overview(
            [income(1, 50000, 2024, month) for month in range(1, 5)],
            records,
            user_id=1,
            month=4,
            year=2024,
            as_of=date(2024, 5, 15),
        )
        self.assertEqual(overview["spending"]["overspending"][0]["category"], "Food")
        self.assertTrue(any(row["label"] == "Unusual Spending" for row in overview["anomalies"]))

    def test_zero_income_is_safe_and_does_not_claim_savings_rate(self):
        overview = build_intelligence_overview(
            [], [expense(1, 1200, 2024, 4)], user_id=1, month=4, year=2024, as_of=date(2024, 4, 20)
        )
        self.assertEqual(overview["summary"]["savings_rate"], Decimal("0.00"))
        self.assertIsNone(overview["features"]["monthly_history"][0]["savings_rate"])

    def test_insufficient_history_never_returns_fabricated_forecast(self):
        overview = build_intelligence_overview(
            [income(1, 50000, 2024, 4)], [expense(1, 30000, 2024, 4)],
            user_id=1, month=4, year=2024, as_of=date(2024, 4, 20)
        )
        self.assertFalse(overview["forecast"]["available"])
        self.assertIsNone(overview["forecast"]["predicted_income"])
        self.assertIsNone(overview["savings"]["predicted_next_month_savings"])

    def test_weighted_moving_average_uses_three_completed_months(self):
        incomes = [income(1, amount, 2024, month) for month, amount in ((1, 50000), (2, 50000), (3, 60000))]
        expenses = [expense(1, amount, 2024, month) for month, amount in ((1, 30000), (2, 32000), (3, 34000))]
        overview = build_intelligence_overview(
            incomes, expenses, user_id=1, month=3, year=2024, as_of=date(2024, 4, 15)
        )
        forecast = overview["forecast"]
        self.assertTrue(forecast["available"])
        self.assertEqual(forecast["method"], "weighted_moving_average")
        self.assertEqual(forecast["historical_months"], 3)
        self.assertEqual(forecast["predicted_income"], Decimal("55000.00"))
        self.assertEqual(forecast["predicted_expenses"], Decimal("32666.67"))
        self.assertEqual(forecast["predicted_savings"], Decimal("22333.33"))

    def test_forecast_requires_contiguous_history_through_previous_month(self):
        rows = [
            {"year": 2024, "month_number": month, "total_income": Decimal("100"), "total_expenses": Decimal("50")}
            for month in (1, 2, 4)
        ]
        result = forecast_cash_flow(rows, as_of=date(2024, 5, 1))
        self.assertFalse(result["available"])
        self.assertIsNone(result["predicted_expenses"])

    def test_risk_engine_returns_insufficient_when_no_observations(self):
        result = score_financial_risk([], {})
        self.assertIsNone(result["score"])
        self.assertEqual(result["coverage_percent"], 0)

    def test_recurring_expenses_require_repeated_real_records(self):
        records = [expense(1, amount, 2024, month, category="Rent") for month, amount in ((1, 12000), (2, 12000), (3, 12500))]
        for index, record in enumerate(records):
            record.description = f"Rent payment {index + 1}"
        overview = build_intelligence_overview(
            [], records, user_id=1, month=3, year=2024, as_of=date(2024, 3, 20)
        )
        self.assertEqual(len(overview["recurring"]), 1)
        self.assertEqual(overview["recurring"][0]["frequency"], "monthly")


    def test_intelligence_route_scopes_rows_to_requested_user(self):
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "intelligence-test.db"
            app = create_app({
                "TESTING": True,
                "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
                "FRONTEND_URL": "http://localhost:5173",
            })
            create_tables(app)
            with app.app_context(), session_scope() as session:
                first = User(name="First", email="first@example.test")
                second = User(name="Second", email="second@example.test")
                first.password_hash = generate_password_hash("First-test-password-123!", method="scrypt")
                second.password_hash = generate_password_hash("Second-test-password-123!", method="scrypt")
                session.add_all([first, second])
                session.flush()
                session.add(Income(user_id=first.id, source="Salary", amount=Decimal("50000"), income_type="Salary", date=date(2024, 4, 10)))
                session.add(Income(user_id=second.id, source="Salary", amount=Decimal("90000"), income_type="Salary", date=date(2024, 4, 10)))
            client = app.test_client()
            login = client.post(
                "/api/auth/login",
                json={"email": "first@example.test", "password": "First-test-password-123!"},
            )
            self.assertEqual(login.status_code, 200)
            response = client.get("/api/intelligence/overview?user_id=1&month=4&year=2024")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["data"]["summary"]["total_income"], 50000)
            self.assertEqual(payload["data"]["user_id"], 1)
            for endpoint in ("forecast", "expense-prediction", "spending", "anomalies", "recurring", "risk", "recommendations", "savings"):
                endpoint_response = client.get(
                    f"/api/intelligence/{endpoint}?user_id=1&month=4&year=2024"
                )
                self.assertEqual(endpoint_response.status_code, 200, endpoint)
                self.assertEqual(endpoint_response.get_json()["status"], "success", endpoint)
            get_engine(app).dispose()


if __name__ == "__main__":
    unittest.main()
