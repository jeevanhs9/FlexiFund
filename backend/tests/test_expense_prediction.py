"""Regression, leakage, security, and HTTP tests for next-month expense ML."""

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
from app.models import Expense, User
from app.services.expense_prediction import (
    FEATURE_NAMES,
    build_time_based_training_rows,
    predict_next_month_expenses,
)
from app.services.intelligence_service import build_intelligence_overview


def _offset_month(year: int, month: int, offset: int) -> tuple[int, int]:
    value = year * 12 + month - 1 + offset
    return value // 12, value % 12 + 1


def _monthly_expenses(values: list[int], *, year: int = 2024) -> list[dict]:
    return [
        {
            "year": year + (index // 12),
            "month_number": index % 12 + 1,
            "total_expenses": Decimal(str(amount)),
            "expense_transaction_count": 1,
        }
        for index, amount in enumerate(values)
    ]


class ExpensePredictionServiceTests(unittest.TestCase):
    def setUp(self):
        # Variance makes the later chronological holdout meaningful without
        # embedding any fake evaluation result in the service.
        self.monthly = _monthly_expenses([
            21000, 22500, 21750, 23900, 25100, 24750,
            26800, 27900, 27300, 29100, 30500, 29800,
        ])
        self.as_of = date(2025, 1, 15)

    def test_feature_generation_uses_only_prior_months(self):
        rows = build_time_based_training_rows(self.monthly, as_of=self.as_of)
        self.assertEqual(rows["feature_names"], list(FEATURE_NAMES))
        self.assertEqual(rows["target_periods"][0], "2024-04")
        # April's label is 23900; the first row may only use Jan–Mar.
        self.assertEqual(rows["features"][0][:5], [21750.0, 22500.0, 21000.0, 21750.0, 750.0])
        self.assertEqual(rows["targets"][0], 23900.0)

    def test_target_change_does_not_change_its_own_features(self):
        changed = [dict(row) for row in self.monthly]
        changed[3]["total_expenses"] = Decimal("999999")
        original = build_time_based_training_rows(self.monthly, as_of=self.as_of)
        altered = build_time_based_training_rows(changed, as_of=self.as_of)
        self.assertEqual(original["features"][0], altered["features"][0])
        self.assertNotEqual(original["targets"][0], altered["targets"][0])

    def test_insufficient_data_returns_no_prediction(self):
        result = predict_next_month_expenses(self.monthly[:11], user_id=7, as_of=self.as_of)
        self.assertFalse(result["available"])
        self.assertIsNone(result["predicted_expenses"])
        self.assertIn("Not enough historical financial data", result["explanation"])

    def test_training_evaluation_prediction_and_safe_artifact_reuse(self):
        with TemporaryDirectory() as directory:
            result = predict_next_month_expenses(
                self.monthly, user_id=7, as_of=self.as_of, model_store_dir=directory
            )
            self.assertTrue(result["available"])
            self.assertGreaterEqual(result["predicted_expenses"], Decimal("0"))
            self.assertEqual(result["training_observations"], 6)
            self.assertEqual(result["validation_observations"], 3)
            self.assertIn(result["selected_model"], {
                "previous_month_baseline", "linear_regression", "random_forest_regressor", "gradient_boosting_regressor",
            })
            self.assertEqual({row["name"] for row in result["candidate_models"]}, {
                "linear_regression", "random_forest_regressor", "gradient_boosting_regressor",
            })
            self.assertGreaterEqual(result["evaluation"]["mae"], 0)
            self.assertGreaterEqual(result["baseline_performance"]["rmse"], 0)
            self.assertTrue((Path(directory) / "expense_prediction_user_7.joblib").is_file())
            loaded = predict_next_month_expenses(
                self.monthly, user_id=7, as_of=self.as_of, model_store_dir=directory
            )
            self.assertEqual(loaded["model_source"], "saved_model")
            self.assertEqual(loaded["predicted_expenses"], result["predicted_expenses"])

    def test_prediction_integrates_with_cash_flow_and_savings(self):
        incomes = [
            SimpleNamespace(user_id=7, amount=Decimal("50000"), date=date(2024, month, 5), income_type="Salary", description=None)
            for month in range(1, 13)
        ]
        expenses = [
            SimpleNamespace(user_id=7, amount=row["total_expenses"], date=date(row["year"], row["month_number"], 10), category="Food", expense_type="Essential", description=None)
            for row in self.monthly
        ]
        overview = build_intelligence_overview(incomes, expenses, user_id=7, as_of=self.as_of)
        prediction = overview["expense_prediction"]
        self.assertTrue(prediction["available"])
        self.assertEqual(overview["forecast"]["predicted_expenses"], prediction["predicted_expenses"])
        self.assertEqual(
            overview["savings"]["predicted_next_month_savings"],
            overview["forecast"]["predicted_savings"],
        )


class ExpensePredictionApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        database_path = Path(self.temp.name) / "prediction-api.sqlite"
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "prediction-api-test-secret-key-0123456789",
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "MODEL_STORE_DIR": str(Path(self.temp.name) / "model-store"),
            "FRONTEND_URL": "http://localhost:5173",
        })
        create_tables(self.app)
        password = "Prediction-test-password-123!"
        with self.app.app_context(), session_scope() as database:
            first = User(name="Model owner", email="model-owner@example.test", password_hash=generate_password_hash(password, method="scrypt"))
            second = User(name="Other account", email="model-other@example.test", password_hash=generate_password_hash(password, method="scrypt"))
            database.add_all([first, second])
            database.flush()
            self.owner_id, self.other_id = first.id, second.id
            for offset, amount in zip(range(-12, 0), [21000, 22500, 21750, 23900, 25100, 24750, 26800, 27900, 27300, 29100, 30500, 29800]):
                year, month = _offset_month(date.today().year, date.today().month, offset)
                database.add(Expense(
                    user_id=first.id, category="Food", amount=Decimal(str(amount)),
                    expense_type="Essential", date=date(year, month, 10),
                ))
        self.owner = self.app.test_client()
        self.other = self.app.test_client()
        self.owner_token = self.owner.post("/api/auth/login", json={"email": "model-owner@example.test", "password": password}).get_json()["data"]["csrf_token"]
        self.other.post("/api/auth/login", json={"email": "model-other@example.test", "password": password})

    def tearDown(self):
        get_engine(self.app).dispose()
        self.temp.cleanup()

    def test_prediction_endpoint_requires_auth_and_scopes_user(self):
        self.assertEqual(self.app.test_client().get("/api/intelligence/expense-prediction").status_code, 401)
        response = self.owner.get("/api/intelligence/expense-prediction")
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()["data"]
        self.assertTrue(payload["available"])
        self.assertIsNotNone(payload["predicted_expenses"])
        self.assertEqual(
            self.other.get(f"/api/intelligence/expense-prediction?user_id={self.owner_id}").status_code,
            403,
        )

    def test_assistant_uses_prediction_service_for_next_month_question(self):
        response = self.owner.post(
            "/api/assistant/chat",
            json={"question": "What will I spend next month?"},
            headers={"Origin": "http://localhost:5173", "X-CSRF-Token": self.owner_token},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()["data"]
        self.assertEqual(data["intent"], "FORECAST")
        self.assertTrue(data["factual_calculation"]["expense_prediction"]["available"])
        self.assertIn("expense model", data["factual_answer"].casefold())


if __name__ == "__main__":
    unittest.main()
