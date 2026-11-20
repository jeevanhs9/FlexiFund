"""Account isolation, intent routing, and provider-fallback tests for Phase 6."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app import create_app
from app.database import create_tables, get_engine, session_scope
from app.models import AssistantMessage, Expense, Income, User
from app.services.llm_service import generate_explanation
from app.services.query_analyzer import Intent, analyze_question


def _offset_month(year: int, month: int, offset: int) -> tuple[int, int]:
    value = year * 12 + month - 1 + offset
    return value // 12, value % 12 + 1


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        database_path = Path(self.temp.name) / "assistant-test.sqlite"
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "phase-six-test-secret-key-0123456789",
                "SESSION_COOKIE_SECURE": False,
                "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
                "FRONTEND_URL": "http://localhost:5173",
                "AI_PROVIDER": "disabled",
                "AI_API_KEY": "",
                "AI_MODEL": "",
            }
        )
        create_tables(self.app)
        self.password = "Assistant-test-password-123!"
        with self.app.app_context(), session_scope() as db:
            user_a = User(
                name="Account A",
                email="assistant-a@example.test",
                password_hash=generate_password_hash(self.password, method="scrypt"),
            )
            user_b = User(
                name="Account B",
                email="assistant-b@example.test",
                password_hash=generate_password_hash(self.password, method="scrypt"),
            )
            db.add_all([user_a, user_b])
            db.flush()
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self._seed_finances(db, self.user_a_id)
            db.add(
                Income(
                    user_id=self.user_b_id,
                    source="Private salary",
                    amount=Decimal("999999"),
                    income_type="Salary",
                    date=date.today().replace(day=min(5, date.today().day)),
                    description="B-only private record text",
                )
            )

        self.client_a = self.app.test_client()
        self.client_b = self.app.test_client()
        self.csrf_a = self._login(self.client_a, "assistant-a@example.test")
        self.csrf_b = self._login(self.client_b, "assistant-b@example.test")
        self.headers_a = {"Origin": "http://localhost:5173", "X-CSRF-Token": self.csrf_a}
        self.headers_b = {"Origin": "http://localhost:5173", "X-CSRF-Token": self.csrf_b}

    def tearDown(self):
        get_engine(self.app).dispose()
        self.temp.cleanup()

    @staticmethod
    def _login(client, email, password="Assistant-test-password-123!"):
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        if response.status_code != 200:
            raise AssertionError(response.get_json())
        return response.get_json()["data"]["csrf_token"]

    @staticmethod
    def _seed_finances(db, user_id):
        today = date.today()
        for age in range(4, 0, -1):
            year, month = _offset_month(today.year, today.month, -age)
            record_date = date(year, month, 5)
            db.add(
                Income(
                    user_id=user_id,
                    source="Salary",
                    amount=Decimal(str(45000 + age * 1000)),
                    income_type="Salary",
                    date=record_date,
                )
            )
            for category, amount, kind in (
                ("Food", 5000 + age * 100, "Essential"),
                ("Rent", 12000, "Essential"),
                ("Transportation", 3000, "Essential"),
            ):
                db.add(
                    Expense(
                        user_id=user_id,
                        category=category,
                        amount=Decimal(str(amount)),
                        expense_type=kind,
                        date=record_date,
                        description="Should stay private from the LLM",
                    )
                )
        current_date = today.replace(day=min(5, today.day))
        db.add(
            Income(
                user_id=user_id,
                source="Salary",
                amount=Decimal("60000"),
                income_type="Salary",
                date=current_date,
            )
        )
        for category, amount, kind in (
            ("Food", 12000, "Essential"),
            ("Rent", 12000, "Essential"),
            ("Shopping", 40000, "Non-Essential"),
        ):
            db.add(
                Expense(
                    user_id=user_id,
                    category=category,
                    amount=Decimal(str(amount)),
                    expense_type=kind,
                    date=current_date,
                    description="Should stay private from the LLM",
                )
            )

    def _chat(self, client, question, *, conversation_id=None, user_id=None, headers=None):
        body = {"question": question}
        if conversation_id:
            body["conversation_id"] = conversation_id
        if user_id is not None:
            body["user_id"] = user_id
        return client.post("/api/assistant/chat", json=body, headers=headers or self.headers_a)

    def test_intent_detection_covers_supported_categories(self):
        examples = {
            "What is my balance?": Intent.BALANCE,
            "Show my income": Intent.INCOME,
            "Show my expenses": Intent.EXPENSE,
            "How much did I spend?": Intent.SPENDING,
            "Where did I spend the most?": Intent.CATEGORY,
            "Do I have a budget?": Intent.BUDGET,
            "How much did I save?": Intent.SAVINGS,
            "What is my forecast for next month?": Intent.FORECAST,
            "What are my financial risks?": Intent.RISK,
            "Can I reach my savings goal?": Intent.GOAL,
            "Why did my expenses increase?": Intent.ANOMALY,
            "What do you recommend?": Intent.RECOMMENDATION,
            "How am I doing financially?": Intent.FINANCIAL_HEALTH,
            "Hello there": Intent.GENERAL,
        }
        for question, expected in examples.items():
            with self.subTest(question=question):
                self.assertEqual(analyze_question(question).intent, expected)

    def test_anonymous_assistant_routes_return_401(self):
        client = self.app.test_client()
        self.assertEqual(client.post("/api/assistant/chat", json={"question": "Show my income"}).status_code, 401)
        self.assertEqual(client.get("/api/assistant/history").status_code, 401)
        self.assertEqual(client.delete("/api/assistant/history").status_code, 401)

    def test_invalid_or_empty_questions_are_rejected(self):
        empty = self.client_a.post("/api/assistant/chat", json={"question": "   "}, headers=self.headers_a)
        self.assertEqual(empty.status_code, 400)
        malformed_id = self.client_a.post(
            "/api/assistant/chat",
            json={"question": "Show my income", "conversation_id": "x" * 36},
            headers=self.headers_a,
        )
        self.assertEqual(malformed_id.status_code, 400)

    def test_chat_uses_phase5_calculations_and_deterministic_fallback(self):
        cases = (
            ("Show my income this month", "INCOME", "60000"),
            ("How much did I spend this month?", "SPENDING", "64000"),
            ("Where did I spend the most?", "CATEGORY", "Shopping"),
            ("How much did I save this month?", "SAVINGS", "-4000"),
            ("What will my expenses look like next month?", "FORECAST", None),
            ("What are my biggest financial risks?", "RISK", None),
            ("Why did my expenses increase?", "ANOMALY", None),
            ("How can I reduce my expenses?", "RECOMMENDATION", None),
        )
        conversation_id = None
        for question, expected_intent, expected_fact in cases:
            response = self._chat(
                self.client_a,
                question,
                conversation_id=conversation_id,
            )
            self.assertEqual(response.status_code, 200, response.get_json())
            data = response.get_json()["data"]
            conversation_id = data["conversation_id"]
            self.assertEqual(data["intent"], expected_intent)
            self.assertEqual(data["explanation_source"], "deterministic_fallback")
            self.assertEqual(data["ai_status"], "not_configured")
            self.assertEqual(len(data["messages"]), 2)
            if expected_fact:
                self.assertIn(expected_fact, json.dumps(data["factual_calculation"]))
            if expected_intent == "FORECAST":
                self.assertTrue(data["factual_calculation"]["forecast_available"])
            if expected_intent == "RISK":
                score = data["factual_calculation"]["health_score"]
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)

    def test_forecast_without_history_is_honest_and_goal_support_is_explicit(self):
        with self.app.app_context(), session_scope() as db:
            fresh = User(
                name="Fresh account",
                email="assistant-fresh@example.test",
                password_hash=generate_password_hash("Fresh-test-password-123!", method="scrypt"),
            )
            db.add(fresh)
            db.flush()
            fresh_id = fresh.id
        fresh_client = self.app.test_client()
        fresh_token = self._login(
            fresh_client,
            "assistant-fresh@example.test",
            "Fresh-test-password-123!",
        )
        fresh_headers = {"Origin": "http://localhost:5173", "X-CSRF-Token": fresh_token}
        forecast = self._chat(fresh_client, "Forecast my expenses", headers=fresh_headers).get_json()["data"]
        self.assertEqual(forecast["intent"], "FORECAST")
        self.assertFalse(forecast["factual_calculation"]["forecast_available"])
        self.assertIn("don't have enough historical financial data", forecast["factual_answer"])
        goal = self._chat(fresh_client, "Can I reach my savings goal?", headers=fresh_headers).get_json()["data"]
        self.assertEqual(goal["intent"], "GOAL")
        self.assertIn("There is no saved personal savings goal", goal["factual_answer"])
        self.assertNotEqual(fresh_id, self.user_a_id)

    def test_body_user_id_and_conversation_id_cannot_cross_accounts(self):
        denied_id = self._chat(
            self.client_a,
            "Show my income",
            user_id=self.user_b_id,
        )
        self.assertEqual(denied_id.status_code, 403)

        created = self._chat(self.client_a, "Show my income")
        conversation_id = created.get_json()["data"]["conversation_id"]
        self.assertEqual(len(created.get_json()["data"]["messages"]), 2)

        self.assertEqual(
            self.client_b.get(f"/api/assistant/history?conversation_id={conversation_id}").status_code,
            404,
        )
        self.assertEqual(
            self.client_b.delete(f"/api/assistant/history?conversation_id={conversation_id}", headers=self.headers_b).status_code,
            404,
        )
        self.assertEqual(
            self._chat(self.client_b, "Show my income", conversation_id=conversation_id, headers=self.headers_b).status_code,
            404,
        )
        own_history = self.client_a.get(f"/api/assistant/history?conversation_id={conversation_id}")
        self.assertEqual(own_history.status_code, 200)
        self.assertEqual(len(own_history.get_json()["data"]["messages"]), 2)
        self.assertNotIn("999999", own_history.get_data(as_text=True))
        self.assertNotIn("B-only private record text", own_history.get_data(as_text=True))

    def test_clear_history_deletes_only_the_signed_in_users_messages(self):
        conversation_id = self._chat(self.client_a, "Show my income").get_json()["data"]["conversation_id"]
        self._chat(self.client_b, "Show my income", headers=self.headers_b)
        cleared = self.client_a.delete("/api/assistant/history", headers=self.headers_a)
        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(cleared.get_json()["data"]["deleted_messages"], 2)
        self.assertEqual(self.client_a.get("/api/assistant/history").get_json()["data"]["messages"], [])
        self.assertEqual(len(self.client_b.get("/api/assistant/history").get_json()["data"]["messages"]), 2)
        with self.app.app_context(), session_scope() as db:
            remaining = db.scalars(select(AssistantMessage).where(AssistantMessage.conversation_id == conversation_id)).all()
            self.assertEqual(remaining, [])

    def test_llm_unavailable_and_malformed_responses_fall_back_safely(self):
        with self.app.app_context():
            current = self.app.config.copy()
            self.app.config.update(AI_PROVIDER="openai_compatible", AI_API_KEY="test-key", AI_MODEL="test-model")
            try:
                with patch("app.services.llm_service.urlopen", side_effect=TimeoutError()):
                    timeout = generate_explanation(question="How am I doing?", facts={"income": 10})
                self.assertEqual(timeout["status"], "unavailable")

                class FakeResponse:
                    def __init__(self, value):
                        self.value = value

                    def __enter__(self):
                        return self

                    def __exit__(self, *_args):
                        return False

                    def read(self):
                        return json.dumps(self.value).encode("utf-8")

                with patch("app.services.llm_service.urlopen", return_value=FakeResponse({"choices": []})):
                    malformed = generate_explanation(question="How am I doing?", facts={"income": 10})
                self.assertEqual(malformed["status"], "malformed_response")
                self.assertIsNone(malformed["text"])
            finally:
                self.app.config.update(current)

    def test_llm_payload_contains_only_compact_verified_facts(self):
        with self.app.app_context():
            self.app.config.update(AI_PROVIDER="openai_compatible", AI_API_KEY="test-key", AI_MODEL="test-model")

            class FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return False

                def read(self):
                    return json.dumps({"choices": [{"message": {"content": "Your recorded income is steady."}}]}).encode()

            with patch("app.services.llm_service.urlopen", return_value=FakeResponse()) as mocked:
                result = generate_explanation(
                    question="How am I doing?",
                    facts={"recorded_income": 60000, "period": "November 2026"},
                )
            self.assertEqual(result["status"], "available")
            request = mocked.call_args.args[0]
            sent_payload = json.loads(request.data.decode())
            self.assertIn("60000", sent_payload["messages"][1]["content"])
            self.assertNotIn("assistant-a@example.test", sent_payload["messages"][1]["content"])
            self.assertNotIn("Should stay private from the LLM", sent_payload["messages"][1]["content"])

    def test_openai_responses_adapter_parses_current_response_shape(self):
        with self.app.app_context():
            self.app.config.update(AI_PROVIDER="openai", AI_API_KEY="test-key", AI_MODEL="test-model")

            class FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return False

                def read(self):
                    return json.dumps({
                        "output": [{
                            "type": "message",
                            "content": [{"type": "output_text", "text": "Use the recorded surplus as context."}],
                        }]
                    }).encode()

            with patch("app.services.llm_service.urlopen", return_value=FakeResponse()) as mocked:
                result = generate_explanation(
                    question="How am I doing?",
                    facts={"recorded_surplus": 5000},
                )
            self.assertEqual(result, {"text": "Use the recorded surplus as context.", "status": "available"})
            request = mocked.call_args.args[0]
            self.assertTrue(request.full_url.endswith("/v1/responses"))
            self.assertFalse(json.loads(request.data.decode())["store"])


if __name__ == "__main__":
    unittest.main()
