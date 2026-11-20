"""Live HTTP integration checks against an isolated localhost Flask server."""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener
from http.cookiejar import CookieJar

from werkzeug.serving import make_server

from app import create_app
from app.database import create_tables, get_engine


def previous_months(count: int) -> list[tuple[int, int]]:
    year, month = date.today().year, date.today().month
    months = []
    for _ in range(count):
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1
        months.append((year, month))
    return list(reversed(months))


class LiveHttpClient:
    def __init__(self, base_url: str, origin: str):
        self.base_url = base_url.rstrip("/")
        self.origin = origin
        self.cookie_jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))
        self.csrf_token: str | None = None

    def request(self, path: str, *, method: str = "GET", body: dict | None = None):
        headers = {"Accept": "application/json", "Origin": self.origin}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if method not in {"GET", "HEAD"} and self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            response = self.opener.open(request, timeout=8)
            status = response.status
            payload = json.loads(response.read().decode("utf-8"))
            response_headers = response.headers
        except HTTPError as error:
            status = error.code
            payload = json.loads(error.read().decode("utf-8"))
            response_headers = error.headers
            error.close()
        data = payload.get("data") if isinstance(payload, dict) else None
        csrf = data.get("csrf_token") if isinstance(data, dict) else None
        if csrf:
            self.csrf_token = csrf
        return status, payload, response_headers

    def register(self, email: str, password: str):
        return self.request(
            "/api/auth/register",
            method="POST",
            body={"name": "Live test", "email": email, "password": password},
        )

    def add_income(self, amount: int, entry_date: date):
        return self.request(
            "/api/income",
            method="POST",
            body={
                "source": "Live test income",
                "amount": amount,
                "income_type": "Salary",
                "date": entry_date.isoformat(),
            },
        )

    def add_expense(self, category: str, amount: int, entry_date: date, kind: str):
        return self.request(
            "/api/expenses",
            method="POST",
            body={
                "category": category,
                "amount": amount,
                "expense_type": kind,
                "date": entry_date.isoformat(),
                "description": "Rent payment" if category == "Rent" else f"{category} cost",
            },
        )


class LiveIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "live-http.db"
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "live-http-session-secret-0123456789abcdef",
                "SESSION_COOKIE_SECURE": False,
                "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
                "FRONTEND_URL": "http://127.0.0.1:5173",
            }
        )
        create_tables(self.app)
        self.server = make_server("127.0.0.1", 0, self.app)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.addCleanup(self._close_server)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.client = LiveHttpClient(self.base_url, "http://127.0.0.1:5173")

    def _close_server(self):
        self.server.shutdown()
        self.server_thread.join(timeout=5)
        get_engine(self.app).dispose()
        self.temporary_directory.cleanup()

    def test_live_auth_finance_dashboard_and_phase5_pipeline(self):
        health_status, health, headers = self.client.request("/api/health")
        self.assertEqual(health_status, 200)
        self.assertEqual(health["database"], "available")
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:5173")
        rider_status, rider_data, _ = self.client.request("/api/demo/rider")
        self.assertEqual(rider_status, 200)
        self.assertEqual(rider_data, {"rider": None, "history": []})

        anonymous_status, anonymous, _ = self.client.request("/api/dashboard")
        self.assertEqual(anonymous_status, 401)
        self.assertNotIn("data", anonymous)

        email = f"live-{threading.get_ident()}@example.test"
        register_status, registration, _ = self.client.register(email, "Live-test-password-123!")
        self.assertEqual(register_status, 201)
        self.assertEqual(registration["data"]["user"]["email"], email)
        user_id = registration["data"]["user"]["id"]

        me_status, current, _ = self.client.request("/api/auth/me")
        self.assertEqual(me_status, 200)
        self.assertEqual(current["data"]["user"]["id"], user_id)
        self.assertTrue(self.client.csrf_token)

        today = date.today()
        for index, (year, month) in enumerate(previous_months(3)):
            record_date = date(year, month, 5)
            income_status, income, _ = self.client.add_income(50000 + 5000 * index, record_date)
            self.assertEqual(income_status, 201)
            self.assertEqual(income["data"]["user_id"], user_id)
            for category, amount, kind in (
                ("Food", 10000 + 2000 * index, "Essential"),
                ("Shopping", 1000 + 500 * index, "Non-Essential"),
                ("Rent", 12000, "Essential"),
            ):
                expense_status, expense, _ = self.client.add_expense(category, amount, record_date, kind)
                self.assertEqual(expense_status, 201)
                self.assertEqual(expense["data"]["user_id"], user_id)

        current_date = today.replace(day=min(5, today.day))
        income_status, income, _ = self.client.add_income(60000, current_date)
        self.assertEqual(income_status, 201)
        baseline_recommendations = self.client.request("/api/intelligence/recommendations")[1]["data"]
        self.assertEqual(self.client.request("/api/expenses")[0], 200)

        for category, amount, kind in (
            ("Food", 10000, "Essential"),
            ("Shopping", 40000, "Non-Essential"),
        ):
            expense_status, _, _ = self.client.add_expense(category, amount, current_date, kind)
            self.assertEqual(expense_status, 201)

        income_status, income_list, _ = self.client.request("/api/income")
        expense_status, expense_list, _ = self.client.request("/api/expenses")
        self.assertEqual(income_status, 200)
        self.assertEqual(expense_status, 200)
        self.assertTrue(all(row["user_id"] == user_id for row in income_list["data"]))
        self.assertTrue(all(row["user_id"] == user_id for row in expense_list["data"]))

        dashboard_status, dashboard, _ = self.client.request("/api/dashboard")
        self.assertEqual(dashboard_status, 200)
        self.assertEqual(dashboard["data"]["total_income"], 60000)
        self.assertEqual(dashboard["data"]["total_expenses"], 50000)
        monthly_status, monthly, _ = self.client.request(f"/api/dashboard/monthly?year={today.year}")
        categories_status, categories, _ = self.client.request("/api/dashboard/expense-categories")
        self.assertEqual(monthly_status, 200)
        self.assertTrue(any(row["income"] > 0 for row in monthly))
        self.assertEqual(categories_status, 200)
        self.assertEqual(categories["Shopping"], 40000)

        overview_status, overview, _ = self.client.request("/api/intelligence/overview")
        self.assertEqual(overview_status, 200)
        self.assertEqual(overview["data"]["user_id"], user_id)
        self.assertEqual(overview["data"]["data_quality"]["valid_rows"], len(income_list["data"]) + len(expense_list["data"]))

        intelligence = {}
        for endpoint in (
            "spending",
            "forecast",
            "expense-prediction",
            "savings",
            "risk",
            "recommendations",
            "anomalies",
            "recurring",
        ):
            status, payload, _ = self.client.request(f"/api/intelligence/{endpoint}")
            self.assertEqual(status, 200, endpoint)
            self.assertEqual(payload["status"], "success", endpoint)
            intelligence[endpoint] = payload["data"]

        forecast = intelligence["forecast"]
        self.assertTrue(forecast["available"])
        self.assertEqual(forecast["historical_months"], 3)
        self.assertAlmostEqual(
            forecast["predicted_savings"],
            round(forecast["predicted_income"] - forecast["predicted_expenses"], 2),
            places=2,
        )
        self.assertEqual(
            intelligence["savings"]["predicted_next_month_savings"],
            forecast["predicted_savings"],
        )
        self.assertFalse(intelligence["expense-prediction"]["available"])
        self.assertGreaterEqual(intelligence["risk"]["score"], 0)
        self.assertLessEqual(intelligence["risk"]["score"], 100)
        self.assertTrue(any(row["category"] == "Shopping" for row in intelligence["anomalies"]))
        self.assertTrue(any(row["category"] == "Rent" for row in intelligence["recurring"]))
        self.assertNotEqual(
            [item["title"] for item in baseline_recommendations],
            [item["title"] for item in intelligence["recommendations"]],
        )
        self.assertTrue(
            any("Shopping" in item["title"] or "Shopping" in item["message"] for item in intelligence["recommendations"])
        )

        assistant_status, assistant, _ = self.client.request(
            "/api/assistant/chat",
            method="POST",
            body={"question": "What will my expenses look like next month?"},
        )
        self.assertEqual(assistant_status, 200)
        assistant_data = assistant["data"]
        self.assertEqual(assistant_data["intent"], "FORECAST")
        self.assertTrue(assistant_data["factual_calculation"]["forecast_available"])
        self.assertIn("estimates", assistant_data["factual_answer"])
        conversation_id = assistant_data["conversation_id"]
        history_status, history, _ = self.client.request(
            f"/api/assistant/history?conversation_id={conversation_id}"
        )
        self.assertEqual(history_status, 200)
        self.assertEqual(len(history["data"]["messages"]), 2)
        clear_status, cleared, _ = self.client.request(
            "/api/assistant/history",
            method="DELETE",
        )
        self.assertEqual(clear_status, 200)
        self.assertEqual(cleared["data"]["deleted_messages"], 2)
        self.assertEqual(self.client.request("/api/assistant/history")[1]["data"]["messages"], [])

        for endpoint in ("profile", "behavior", "budget", "goals", "recommendations", "insights"):
            status, payload, _ = self.client.request(f"/api/personalization/{endpoint}")
            self.assertEqual(status, 200, endpoint)
            self.assertEqual(payload["status"], "success", endpoint)

        goal_status, goal_result, _ = self.client.request(
            "/api/personalization/goals",
            method="POST",
            body={
                "name": "Live emergency reserve",
                "target_amount": 25000,
                "current_amount": 2500,
                "target_date": (date.today() + timedelta(days=150)).isoformat(),
                "priority": "high",
                "category": "Emergency fund",
            },
        )
        self.assertEqual(goal_status, 201, goal_result)
        goal_id = goal_result["data"]["goals"][0]["id"]
        self.assertGreaterEqual(goal_result["data"]["goals"][0]["progress_percent"], 9.9)

        before_scenario = self.client.request("/api/expenses")[1]["data"]
        what_if_status, what_if, _ = self.client.request(
            "/api/personalization/what-if",
            method="POST",
            body={"name": "Live shopping adjustment", "changes": [{"change_type": "reduce_expense_category", "category": "Shopping", "amount": 2000}]},
        )
        self.assertEqual(what_if_status, 200, what_if)
        self.assertEqual(what_if["data"]["status"], "SCENARIO")
        self.assertEqual(what_if["data"]["comparison"]["monthly_surplus_change"], 2000)
        compare_status, comparison, _ = self.client.request(
            "/api/personalization/scenario",
            method="POST",
            body={"changes": [{"change_type": "increase_income", "amount": 1000}]},
        )
        self.assertEqual(compare_status, 200, comparison)
        self.assertEqual(comparison["data"]["comparison"]["monthly_surplus_change"], 1000)
        assistant_scenario_status, assistant_scenario, _ = self.client.request(
            "/api/assistant/chat",
            method="POST",
            body={"question": "What if I reduce Shopping by ₹2,000?"},
        )
        self.assertEqual(assistant_scenario_status, 200, assistant_scenario)
        self.assertEqual(assistant_scenario["data"]["intent"], "SCENARIO")
        self.assertEqual(assistant_scenario["data"]["factual_calculation"]["status"], "SCENARIO")
        after_scenario = self.client.request("/api/expenses")[1]["data"]
        self.assertEqual(before_scenario, after_scenario)

        second_client = LiveHttpClient(self.base_url, "http://127.0.0.1:5173")
        second_register_status, _, _ = second_client.register(
            f"personal-isolation-{threading.get_ident()}@example.test",
            "Second-live-password-123!",
        )
        self.assertEqual(second_register_status, 201)
        self.assertEqual(second_client.request("/api/personalization/goals")[1]["data"]["goals"], [])
        self.assertEqual(second_client.request(f"/api/personalization/profile?user_id={user_id}")[0], 403)
        self.assertEqual(second_client.request(f"/api/personalization/goals/{goal_id}", method="PUT", body={"name": "Foreign goal"})[0], 404)
        self.assertEqual(second_client.request(f"/api/personalization/goals/{goal_id}", method="DELETE")[0], 404)

        logout_status, _, _ = self.client.request("/api/auth/logout", method="POST", body={})
        self.assertEqual(logout_status, 200)
        self.assertEqual(self.client.request("/api/auth/me")[0], 401)

    def test_live_fresh_account_forecast_is_unavailable(self):
        email = f"fresh-{threading.get_ident()}@example.test"
        status, _, _ = self.client.register(email, "Fresh-test-password-123!")
        self.assertEqual(status, 201)
        income_status, _, _ = self.client.add_income(50000, date.today().replace(day=min(5, date.today().day)))
        self.assertEqual(income_status, 201)
        forecast_status, forecast, _ = self.client.request("/api/intelligence/forecast")
        self.assertEqual(forecast_status, 200)
        self.assertFalse(forecast["data"]["available"])
        self.assertIsNone(forecast["data"]["predicted_income"])
        self.assertIn("Insufficient historical data", forecast["data"]["explanation"])
        assistant_status, assistant, _ = self.client.request(
            "/api/assistant/chat",
            method="POST",
            body={"question": "What will my expenses look like next month?"},
        )
        self.assertEqual(assistant_status, 200)
        self.assertFalse(assistant["data"]["factual_calculation"]["forecast_available"])
        self.assertIn("don't have enough historical financial data", assistant["data"]["factual_answer"])

    def test_live_ml_prediction_and_account_isolation(self):
        email = f"ml-live-{threading.get_ident()}@example.test"
        status, registration, _ = self.client.register(email, "ML-live-test-password-123!")
        self.assertEqual(status, 201)
        user_id = registration["data"]["user"]["id"]
        amounts = [21000, 22500, 21750, 23900, 25100, 24750, 26800, 27900, 27300, 29100, 30500, 29800]
        for (year, month), amount in zip(previous_months(12), amounts):
            entry_status, _, _ = self.client.add_expense("Food", amount, date(year, month, 10), "Essential")
            self.assertEqual(entry_status, 201)
        before = self.client.request("/api/expenses")[1]["data"]
        prediction_status, prediction, _ = self.client.request("/api/intelligence/expense-prediction")
        self.assertEqual(prediction_status, 200)
        result = prediction["data"]
        self.assertTrue(result["available"])
        self.assertIn(result["selected_model"], {"previous_month_baseline", "linear_regression", "random_forest_regressor", "gradient_boosting_regressor"})
        self.assertEqual(result["validation_observations"], 3)
        overview_status, overview, _ = self.client.request("/api/intelligence/overview")
        self.assertEqual(overview_status, 200)
        self.assertEqual(overview["data"]["forecast"]["predicted_expenses"], result["predicted_expenses"])
        assistant_status, assistant, _ = self.client.request(
            "/api/assistant/chat", method="POST", body={"question": "What will I spend next month?"}
        )
        self.assertEqual(assistant_status, 200)
        self.assertTrue(assistant["data"]["factual_calculation"]["expense_prediction"]["available"])
        self.assertEqual(before, self.client.request("/api/expenses")[1]["data"])
        other = LiveHttpClient(self.base_url, "http://127.0.0.1:5173")
        other.register(f"ml-other-{threading.get_ident()}@example.test", "ML-other-test-password-123!")
        self.assertEqual(other.request(f"/api/intelligence/expense-prediction?user_id={user_id}")[0], 403)


if __name__ == "__main__":
    unittest.main()
