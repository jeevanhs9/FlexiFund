"""Integration tests for finance and dashboard routes using temporary data."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from app import create_app
from app.constants import DEMO_USER_EMAIL
from app.database import create_tables, get_engine, session_scope
from app.models import User


class FinanceApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "finance-test.db"
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
                "FRONTEND_URL": "http://localhost:5173",
            }
        )
        create_tables(self.app)
        with self.app.app_context(), session_scope() as session:
            demo_user = User(
                name="Demo",
                email=DEMO_USER_EMAIL,
                password_hash=generate_password_hash("Demo-test-password-123!", method="scrypt"),
            )
            other_user = User(
                name="Other",
                email="other@example.test",
                password_hash=generate_password_hash("Other-test-password-123!", method="scrypt"),
            )
            session.add_all([demo_user, other_user])
            session.flush()
            self.demo_user_id = demo_user.id
            self.other_user_id = other_user.id
        self.client = self.app.test_client()
        login_response = self.client.post(
            "/api/auth/login",
            json={"email": DEMO_USER_EMAIL, "password": "Demo-test-password-123!"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.csrf_token = login_response.get_json()["data"]["csrf_token"]
        self.write_headers = {"X-CSRF-Token": self.csrf_token}

    def tearDown(self):
        get_engine(self.app).dispose()
        self.temporary_directory.cleanup()

    def add_income(self, *, user_id: int, amount: int, entry_date: str = "2024-04-10"):
        return self.client.post(
            "/api/income",
            json={
                "user_id": user_id,
                "source": "Salary",
                "amount": amount,
                "income_type": "Salary",
                "date": entry_date,
                "description": "Test income",
            },
            headers=self.write_headers,
        )

    def add_expense(
        self,
        *,
        user_id: int,
        amount: int,
        category: str = "Food",
        expense_type: str = "Essential",
        entry_date: str = "2024-04-10",
    ):
        return self.client.post(
            "/api/expenses",
            json={
                "user_id": user_id,
                "category": category,
                "amount": amount,
                "expense_type": expense_type,
                "date": entry_date,
                "description": "Test expense",
            },
            headers=self.write_headers,
        )

    def test_finance_create_read_round_trip_and_default_account_scope(self):
        income_response = self.add_income(user_id=self.demo_user_id, amount=50000)
        expense_response = self.add_expense(
            user_id=self.demo_user_id, amount=2500, category="Food"
        )
        self.assertEqual(income_response.status_code, 201)
        self.assertEqual(expense_response.status_code, 201)
        self.assertEqual(income_response.get_json()["data"]["amount"], 50000)
        self.assertEqual(expense_response.get_json()["data"]["category"], "Food")

        other_client = self.app.test_client()
        other_login = other_client.post(
            "/api/auth/login",
            json={"email": "other@example.test", "password": "Other-test-password-123!"},
        )
        self.assertEqual(other_login.status_code, 200)
        other_csrf = {"X-CSRF-Token": other_login.get_json()["data"]["csrf_token"]}
        other_income = other_client.post(
            "/api/income",
            json={"source": "Salary", "amount": 99000, "income_type": "Salary", "date": "2024-04-10"},
            headers=other_csrf,
        )
        other_expense = other_client.post(
            "/api/expenses",
            json={"category": "Food", "amount": 88000, "expense_type": "Essential", "date": "2024-04-10"},
            headers=other_csrf,
        )
        self.assertEqual(other_income.status_code, 201)
        self.assertEqual(other_expense.status_code, 201)

        income_rows = self.client.get("/api/income").get_json()["data"]
        expense_rows = self.client.get("/api/expenses").get_json()["data"]
        self.assertEqual([row["user_id"] for row in income_rows], [self.demo_user_id])
        self.assertEqual([row["user_id"] for row in expense_rows], [self.demo_user_id])
        self.assertEqual(income_rows[0]["amount"], 50000)
        self.assertEqual(expense_rows[0]["amount"], 2500)
        self.assertEqual(
            self.client.get(f"/api/income?user_id={self.other_user_id}").status_code,
            403,
        )
        self.assertEqual(
            self.client.get(f"/api/expenses?user_id={self.other_user_id}").status_code,
            403,
        )

    def test_dashboard_summary_categories_and_monthly_totals(self):
        self.assertEqual(self.add_income(user_id=self.demo_user_id, amount=50000).status_code, 201)
        expenses = [
            ("Rent", 15000, "Essential"),
            ("Food", 5000, "Essential"),
            ("Transportation", 3000, "Essential"),
            ("Other", 5000, "Essential"),
            ("Shopping", 2000, "Non-Essential"),
        ]
        for category, amount, expense_type in expenses:
            response = self.add_expense(
                user_id=self.demo_user_id,
                amount=amount,
                category=category,
                expense_type=expense_type,
            )
            self.assertEqual(response.status_code, 201, response.get_json())

        dashboard = self.client.get("/api/dashboard?month=4&year=2024").get_json()["data"]
        self.assertEqual(dashboard["total_income"], 50000)
        self.assertEqual(dashboard["total_expenses"], 30000)
        self.assertEqual(dashboard["surplus"], 20000)
        self.assertEqual(dashboard["savings_rate"], 40.0)
        self.assertEqual(dashboard["expense_ratio"], 60.0)
        self.assertEqual(dashboard["essential_expenses"], 28000)
        self.assertEqual(dashboard["non_essential_expenses"], 2000)

        categories = self.client.get(
            "/api/dashboard/expense-categories?month=4&year=2024"
        ).get_json()
        self.assertEqual(categories["Rent"], 15000)
        self.assertEqual(categories["Food"], 5000)
        self.assertEqual(sum(categories.values()), 30000)

        monthly = self.client.get("/api/dashboard/monthly?year=2024").get_json()
        april = next(row for row in monthly if row["month"] == "April")
        self.assertEqual(april["income"], 50000)
        self.assertEqual(april["expenses"], 30000)
        self.assertEqual(april["surplus"], 20000)

    def test_validation_and_unknown_user_errors_are_client_errors(self):
        bad_requests = [
            (
                "/api/income",
                {
                    "user_id": self.demo_user_id,
                    "source": "Salary",
                    "amount": 0,
                    "income_type": "Salary",
                    "date": "2024-04-10",
                },
            ),
            (
                "/api/income",
                {
                    "user_id": self.demo_user_id,
                    "source": "Salary",
                    "amount": 100,
                    "income_type": "Salary",
                    "date": "not-a-date",
                },
            ),
            (
                "/api/expenses",
                {
                    "user_id": self.demo_user_id,
                    "category": "MadeUp",
                    "amount": 100,
                    "expense_type": "Essential",
                    "date": "2024-04-10",
                },
            ),
        ]
        for endpoint, body in bad_requests:
            response = self.client.post(endpoint, json=body, headers=self.write_headers)
            self.assertEqual(response.status_code, 400, response.get_json())
            self.assertIn("message", response.get_json())

        self.assertEqual(self.add_income(user_id=999999, amount=100).status_code, 403)
        self.assertEqual(self.add_expense(user_id=999999, amount=100).status_code, 403)
        self.assertEqual(self.client.get("/api/income?user_id=invalid").status_code, 400)
        self.assertEqual(self.client.get("/api/expenses?month=13").status_code, 400)

    def test_health_reports_database_connectivity(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["database"], "available")

        with patch("app.routes.health.session_scope", side_effect=SQLAlchemyError("offline")):
            unavailable = self.client.get("/api/health")
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(unavailable.get_json()["database"], "unavailable")

    def test_unseeded_synthetic_rider_returns_empty_optional_data(self):
        response = self.client.get("/api/demo/rider")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"rider": None, "history": []})

    def test_user_creation_normalizes_email_and_rejects_duplicate(self):
        response = self.client.post(
            "/api/users", json={"name": " New user ", "email": "NEW@EXAMPLE.TEST"}, headers=self.write_headers
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["data"]["email"], "new@example.test")

        duplicate = self.client.post(
            "/api/users", json={"name": "Duplicate", "email": "new@example.test"}, headers=self.write_headers
        )
        self.assertEqual(duplicate.status_code, 409)


if __name__ == "__main__":
    unittest.main()
