"""Authentication and horizontal-authorization regression tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest
from sqlalchemy import inspect
from werkzeug.security import generate_password_hash

from app import create_app
from app.database import create_tables, get_engine, session_scope
from app.models import Expense, Income, User


def previous_months(count: int) -> list[tuple[int, int]]:
    year, month = date.today().year, date.today().month
    result = []
    for _ in range(count):
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1
        result.append((year, month))
    return list(reversed(result))


class AuthenticationSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "auth-test.db"
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-only-session-secret-0123456789abcdef",
                "SESSION_COOKIE_SECURE": False,
                "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
                "FRONTEND_URL": "http://localhost:5173",
            }
        )
        create_tables(self.app)
        password_a = "Account-A-test-password-123!"
        password_b = "Account-B-test-password-456!"
        password_c = "Account-C-test-password-789!"
        with self.app.app_context(), session_scope() as db:
            self.user_a = User(
                name="Account A",
                email="account-a@example.test",
                password_hash=generate_password_hash(password_a, method="scrypt"),
            )
            self.user_b = User(
                name="Account B",
                email="account-b@example.test",
                password_hash=generate_password_hash(password_b, method="scrypt"),
            )
            self.user_c = User(
                name="Account C",
                email="account-c@example.test",
                password_hash=generate_password_hash(password_c, method="scrypt"),
            )
            db.add_all([self.user_a, self.user_b, self.user_c])
            db.flush()
            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id
            self.user_c_id = self.user_c.id

            current_month = date.today().replace(day=5)
            db.add_all(
                [
                    Income(
                        user_id=self.user_a_id,
                        source="Salary",
                        amount=Decimal("50000"),
                        income_type="Salary",
                        date=current_month,
                    ),
                    Expense(
                        user_id=self.user_a_id,
                        category="Food",
                        amount=Decimal("20000"),
                        expense_type="Essential",
                        date=current_month,
                    ),
                    Income(
                        user_id=self.user_b_id,
                        source="Business",
                        amount=Decimal("99000"),
                        income_type="Business",
                        date=current_month,
                    ),
                    Expense(
                        user_id=self.user_b_id,
                        category="Shopping",
                        amount=Decimal("88000"),
                        expense_type="Non-Essential",
                        date=current_month,
                    ),
                ]
            )
            for index, (year, month) in enumerate(previous_months(3)):
                db.add_all(
                    [
                        Income(
                            user_id=self.user_a_id,
                            source="Salary",
                            amount=Decimal(50000 + 5000 * index),
                            income_type="Salary",
                            date=date(year, month, 5),
                        ),
                        Expense(
                            user_id=self.user_a_id,
                            category="Food",
                            amount=Decimal(5000 + 1000 * index),
                            expense_type="Essential",
                            date=date(year, month, 8),
                        ),
                        Expense(
                            user_id=self.user_a_id,
                            category="Shopping",
                            amount=Decimal(1000 + 500 * index),
                            expense_type="Non-Essential",
                            date=date(year, month, 12),
                        ),
                        Income(
                            user_id=self.user_b_id,
                            source="Business",
                            amount=Decimal("30000"),
                            income_type="Business",
                            date=date(year, month, 5),
                        ),
                        Expense(
                            user_id=self.user_b_id,
                            category="Rent",
                            amount=Decimal("35000"),
                            expense_type="Essential",
                            date=date(year, month, 8),
                        ),
                        Income(
                            user_id=self.user_c_id,
                            source="Salary",
                            amount=Decimal("50000"),
                            income_type="Salary",
                            date=date(year, month, 5),
                        ),
                        Expense(
                            user_id=self.user_c_id,
                            category="Rent",
                            amount=Decimal("50000"),
                            expense_type="Essential",
                            date=date(year, month, 8),
                        ),
                    ]
                )
        self.password_a = password_a
        self.password_b = password_b
        self.password_c = password_c
        self.client = self.app.test_client()

    def tearDown(self):
        get_engine(self.app).dispose()
        self.temporary_directory.cleanup()

    def login(self, email: str, password: str):
        response = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        token = response.get_json()["data"]["csrf_token"]
        return {"X-CSRF-Token": token}

    def test_register_hashes_password_and_supports_session_lifecycle(self):
        client = self.app.test_client()
        weak = client.post(
            "/api/auth/register",
            json={"name": "New User", "email": "new@example.test", "password": "short"},
        )
        self.assertEqual(weak.status_code, 400)

        registration = client.post(
            "/api/auth/register",
            json={
                "name": "New User",
                "email": " New@Example.Test ",
                "password": "Strong-test-password-789!",
            },
        )
        self.assertEqual(registration.status_code, 201, registration.get_json())
        payload = registration.get_json()["data"]
        self.assertEqual(payload["user"]["email"], "new@example.test")
        self.assertNotIn("password", payload)
        self.assertNotIn("password_hash", payload["user"])
        cookie = registration.headers["Set-Cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)
        self.assertIn("expires=", cookie)

        with self.app.app_context(), session_scope() as db:
            created = db.query(User).filter_by(email="new@example.test").one()
            self.assertNotEqual(created.password_hash, "Strong-test-password-789!")
            self.assertTrue(created.password_hash.startswith("scrypt:"))

        current = client.get("/api/auth/me")
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.get_json()["data"]["user"]["email"], "new@example.test")
        csrf = current.get_json()["data"]["csrf_token"]
        replay_client = self.app.test_client()
        replay_client.set_cookie("session", client.get_cookie("session").value)
        logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(client.get("/api/auth/me").status_code, 401)
        self.assertEqual(replay_client.get("/api/auth/me").status_code, 401)

        bad_login = client.post(
            "/api/auth/login",
            json={"email": "new@example.test", "password": "wrong-password"},
        )
        self.assertEqual(bad_login.status_code, 401)
        good_login = client.post(
            "/api/auth/login",
            json={"email": "new@example.test", "password": "Strong-test-password-789!"},
        )
        self.assertEqual(good_login.status_code, 200)

    def test_all_financial_apis_reject_anonymous_requests(self):
        client = self.app.test_client()
        paths = [
            "/api/income",
            "/api/expenses",
            "/api/dashboard",
            "/api/dashboard/monthly",
            "/api/dashboard/expense-categories",
            "/api/intelligence/overview",
            "/api/intelligence/forecast",
            "/api/intelligence/spending",
            "/api/intelligence/anomalies",
            "/api/intelligence/recurring",
            "/api/intelligence/risk",
            "/api/intelligence/recommendations",
            "/api/intelligence/savings",
        ]
        for path in paths:
            response = client.get(path)
            self.assertEqual(response.status_code, 401, path)
            self.assertNotIn("data", response.get_json(), path)
        self.assertEqual(client.get("/api/health").status_code, 200)
        self.assertEqual(
            client.post("/api/income", json={"amount": 100}).status_code,
            401,
        )

    def test_authenticated_user_cannot_select_another_accounts_data(self):
        csrf_headers = self.login("account-a@example.test", self.password_a)
        own_income = self.client.get("/api/income")
        own_expenses = self.client.get("/api/expenses")
        own_dashboard = self.client.get("/api/dashboard")
        own_intelligence = self.client.get("/api/intelligence/overview")
        self.assertEqual(own_income.status_code, 200)
        self.assertTrue(all(row["user_id"] == self.user_a_id for row in own_income.get_json()["data"]))
        self.assertTrue(all(row["user_id"] == self.user_a_id for row in own_expenses.get_json()["data"]))
        self.assertEqual(own_dashboard.get_json()["data"]["user_id"], self.user_a_id)
        self.assertEqual(own_dashboard.get_json()["data"]["total_income"], 50000)
        self.assertEqual(own_intelligence.get_json()["data"]["user_id"], self.user_a_id)

        targets = [
            "/api/income",
            "/api/expenses",
            "/api/dashboard",
            "/api/dashboard/monthly",
            "/api/dashboard/expense-categories",
            "/api/intelligence/overview",
            "/api/intelligence/forecast",
            "/api/intelligence/spending",
            "/api/intelligence/anomalies",
            "/api/intelligence/recurring",
            "/api/intelligence/risk",
            "/api/intelligence/recommendations",
            "/api/intelligence/savings",
        ]
        for path in targets:
            response = self.client.get(f"{path}?user_id={self.user_b_id}")
            self.assertEqual(response.status_code, 403, path)
            self.assertNotIn("data", response.get_json(), path)

        other_client = self.app.test_client()
        other_login = other_client.post(
            "/api/auth/login",
            json={"email": "account-b@example.test", "password": self.password_b},
        )
        self.assertEqual(other_login.status_code, 200)
        other_income = other_client.get("/api/income")
        self.assertTrue(all(row["user_id"] == self.user_b_id for row in other_income.get_json()["data"]))
        self.assertEqual(
            other_client.get(f"/api/dashboard?user_id={self.user_a_id}").status_code,
            403,
        )

        blocked_income = self.client.post(
            "/api/income",
            json={
                "user_id": self.user_b_id,
                "source": "Salary",
                "amount": 1,
                "income_type": "Salary",
                "date": date.today().isoformat(),
            },
            headers=csrf_headers,
        )
        self.assertEqual(blocked_income.status_code, 403)
        blocked_expense = self.client.post(
            "/api/expenses",
            json={
                "user_id": self.user_b_id,
                "category": "Food",
                "amount": 1,
                "expense_type": "Essential",
                "date": date.today().isoformat(),
            },
            headers=csrf_headers,
        )
        self.assertEqual(blocked_expense.status_code, 403)

    def test_csrf_origin_and_invalid_cookie_are_rejected(self):
        self.login("account-a@example.test", self.password_a)
        body = {
            "source": "Salary",
            "amount": 1,
            "income_type": "Salary",
            "date": date.today().isoformat(),
        }
        no_csrf = self.client.post("/api/income", json=body)
        self.assertEqual(no_csrf.status_code, 403)
        wrong_origin = self.client.post(
            "/api/income",
            json=body,
            headers={"X-CSRF-Token": "wrong", "Origin": "https://attacker.example"},
        )
        self.assertEqual(wrong_origin.status_code, 403)

        invalid_client = self.app.test_client()
        invalid_client.set_cookie("session", "tampered-session-cookie")
        self.assertEqual(invalid_client.get("/api/dashboard").status_code, 401)

    def test_forecast_and_recommendations_use_this_users_real_history(self):
        self.login("account-a@example.test", self.password_a)
        forecast = self.client.get("/api/intelligence/forecast").get_json()["data"]
        savings = self.client.get("/api/intelligence/savings").get_json()["data"]
        risk = self.client.get("/api/intelligence/risk").get_json()["data"]
        recommendations = self.client.get("/api/intelligence/recommendations").get_json()["data"]

        self.assertTrue(forecast["available"])
        self.assertEqual(forecast["historical_months"], 3)
        self.assertEqual(
            forecast["predicted_savings"],
            forecast["predicted_income"] - forecast["predicted_expenses"],
        )
        self.assertEqual(savings["predicted_next_month_savings"], forecast["predicted_savings"])
        self.assertGreaterEqual(risk["score"], 0)
        self.assertLessEqual(risk["score"], 100)
        self.assertTrue(any("Food" in item["title"] or "Food" in item["message"] for item in recommendations))

        with self.app.app_context(), session_scope() as db:
            db.add(
                Expense(
                    user_id=self.user_a_id,
                    category="Shopping",
                    amount=Decimal("40000"),
                    expense_type="Non-Essential",
                    date=date.today().replace(day=12),
                )
            )
        changed = self.client.get("/api/intelligence/recommendations").get_json()["data"]
        self.assertTrue(any("Shopping" in item["title"] or "Shopping" in item["message"] for item in changed))

        self.client.post(
            "/api/auth/login",
            json={"email": "account-b@example.test", "password": self.password_b},
        )
        deficit_forecast = self.client.get("/api/intelligence/forecast").get_json()["data"]
        deficit_savings = self.client.get("/api/intelligence/savings").get_json()["data"]
        deficit_risk = self.client.get("/api/intelligence/risk").get_json()["data"]
        self.assertLess(deficit_forecast["predicted_savings"], 0)
        self.assertEqual(deficit_savings["potential_negative_cash_flow"], True)
        self.assertLess(deficit_risk["score"], risk["score"])

        self.client.post(
            "/api/auth/login",
            json={"email": "account-c@example.test", "password": self.password_c},
        )
        zero_forecast = self.client.get("/api/intelligence/forecast").get_json()["data"]
        zero_savings = self.client.get("/api/intelligence/savings").get_json()["data"]
        self.assertEqual(zero_forecast["predicted_savings"], 0)
        self.assertEqual(zero_savings["predicted_next_month_savings"], 0)

    def test_existing_users_table_gets_only_additive_auth_columns(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        database_path = Path(directory.name) / "legacy.db"
        legacy_db = sqlite3.connect(database_path)
        try:
            legacy_db.execute(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(120) NOT NULL, "
                "email VARCHAR(320) NOT NULL UNIQUE, created_at DATETIME NOT NULL)"
            )
            legacy_db.execute(
                "INSERT INTO users (id, name, email, created_at) VALUES (1, 'Legacy', 'legacy@example.test', '2024-01-01')"
            )
            legacy_db.commit()
        finally:
            legacy_db.close()

        app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "legacy-test-session-secret-0123456789abcdef",
                "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            }
        )
        try:
            schema = inspect(get_engine(app))
            columns = {column["name"] for column in schema.get_columns("users")}
            self.assertIn("password_hash", columns)
            self.assertIn("session_version", columns)
            self.assertTrue(schema.has_table("financial_goals"))
            self.assertTrue(schema.has_table("goal_contributions"))
            with app.app_context(), session_scope() as db:
                self.assertEqual(db.query(User).count(), 1)
                legacy_user = db.get(User, 1)
                self.assertIsNone(legacy_user.password_hash)
                self.assertEqual(legacy_user.session_version, 0)
        finally:
            get_engine(app).dispose()


if __name__ == "__main__":
    unittest.main()
