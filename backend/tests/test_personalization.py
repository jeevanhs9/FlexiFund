"""Phase 7 financial personalization, scenario and account-isolation tests."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from app import create_app
from app.database import create_tables, get_engine, session_scope
from app.models import Expense, FinancialGoal, GoalContribution, Income, User
from app.services.adaptive_budget import build_adaptive_budget
from app.services.behavior_analyzer import build_behavior_analysis
from app.services.financial_profile import build_financial_profile
from app.services.goal_engine import build_goal_plan
from app.services.intelligence_service import build_intelligence_overview
from app.services.personalized_recommendations import build_personalized_recommendations
from app.services.scenario_engine import simulate_scenario
from app.schemas import ScenarioChange


def previous_months(count: int) -> list[tuple[int, int]]:
    year, month = date.today().year, date.today().month
    result = []
    for _ in range(count):
        month -= 1
        if month == 0:
            year -= 1
            month = 12
        result.append((year, month))
    return list(reversed(result))


def fixture_snapshot(goal_rows=None, contributions=None):
    today = date.today()
    user_id = 1
    incomes = []
    expenses = []
    for index, (year, month) in enumerate(previous_months(3)):
        entry_date = date(year, month, 10)
        incomes.append(SimpleNamespace(id=index + 1, user_id=user_id, amount=Decimal(50000 + 2000 * index), date=entry_date, income_type="Salary", description="Salary"))
        expenses.extend(
            [
                SimpleNamespace(id=100 + index * 2, user_id=user_id, amount=Decimal(10000 + 1000 * index), date=entry_date, category="Food", expense_type="Essential", description="Food"),
                SimpleNamespace(id=101 + index * 2, user_id=user_id, amount=Decimal("12000"), date=entry_date, category="Rent", expense_type="Essential", description="Rent"),
            ]
        )
    current_date = today.replace(day=min(10, today.day))
    incomes.append(SimpleNamespace(id=10, user_id=user_id, amount=Decimal("60000"), date=current_date, income_type="Salary", description="Salary"))
    expenses.extend(
        [
            SimpleNamespace(id=110, user_id=user_id, amount=Decimal("15000"), date=current_date, category="Food", expense_type="Essential", description="Food"),
            SimpleNamespace(id=111, user_id=user_id, amount=Decimal("12000"), date=current_date, category="Rent", expense_type="Essential", description="Rent"),
        ]
    )
    overview = build_intelligence_overview(incomes, expenses, user_id=user_id, as_of=today)
    return {
        "user_id": user_id,
        "incomes": incomes,
        "expenses": expenses,
        "goals": goal_rows or [],
        "goal_contributions": contributions or [],
        "overview": overview,
    }


class PersonalizationServiceTests(unittest.TestCase):
    def test_profile_uses_observed_months_and_rejects_missing_cash_flow(self):
        snapshot = fixture_snapshot()
        profile = build_financial_profile(snapshot)
        self.assertEqual(profile["average_monthly_income"], Decimal("54000.00"))
        self.assertEqual(profile["average_monthly_expenses"], Decimal("24000.00"))
        self.assertIsNotNone(profile["average_monthly_surplus"])
        self.assertEqual(profile["cash_flow_month_count"], 4)

        empty = fixture_snapshot()
        empty["incomes"] = []
        empty["expenses"] = []
        empty["overview"] = build_intelligence_overview([], [], user_id=1, as_of=date.today())
        empty_profile = build_financial_profile(empty)
        self.assertFalse(empty_profile["available"])
        self.assertIsNone(empty_profile["average_monthly_surplus"])
        self.assertIsNone(empty_profile["average_savings_rate_percent"])

    def test_behavior_detects_increasing_category_and_requires_history_for_classification(self):
        snapshot = fixture_snapshot()
        profile = build_financial_profile(snapshot)
        behavior = build_behavior_analysis(snapshot, profile)
        food = next(row for row in behavior["category_trends"] if row["category"] == "Food")
        self.assertEqual(food["status"], "increasing")
        self.assertTrue(any(item["type"] == "category_trend" and "Food" in item["message"] for item in behavior["insights"]))
        self.assertNotEqual(behavior["behavioral_classification"]["label"], "Insufficient data")

        insufficient = fixture_snapshot()
        insufficient["incomes"] = insufficient["incomes"][-1:]
        insufficient["expenses"] = insufficient["expenses"][-2:]
        insufficient["overview"] = build_intelligence_overview(insufficient["incomes"], insufficient["expenses"], user_id=1, as_of=date.today())
        result = build_behavior_analysis(insufficient, build_financial_profile(insufficient))
        self.assertEqual(result["behavioral_classification"]["label"], "Insufficient data")

        stable_snapshot = fixture_snapshot()
        latest_food = max(row.date for row in stable_snapshot["expenses"] if row.category == "Food")
        previous_food = sorted((row for row in stable_snapshot["expenses"] if row.category == "Food" and row.date < latest_food), key=lambda row: row.date)[-1]
        for row in stable_snapshot["expenses"]:
            if row.category == "Food" and row.date == latest_food:
                row.amount = previous_food.amount
        stable_snapshot["overview"] = build_intelligence_overview(stable_snapshot["incomes"], stable_snapshot["expenses"], user_id=1, as_of=date.today())
        stable_behavior = build_behavior_analysis(stable_snapshot, build_financial_profile(stable_snapshot))
        self.assertEqual(next(row for row in stable_behavior["category_trends"] if row["category"] == "Food")["status"], "stable")

        decreasing_snapshot = fixture_snapshot()
        latest_food = max(row.date for row in decreasing_snapshot["expenses"] if row.category == "Food")
        for row in decreasing_snapshot["expenses"]:
            if row.category == "Food" and row.date == latest_food:
                row.amount = Decimal("8000")
        decreasing_snapshot["overview"] = build_intelligence_overview(decreasing_snapshot["incomes"], decreasing_snapshot["expenses"], user_id=1, as_of=date.today())
        decreasing_behavior = build_behavior_analysis(decreasing_snapshot, build_financial_profile(decreasing_snapshot))
        self.assertEqual(next(row for row in decreasing_behavior["category_trends"] if row["category"] == "Food")["status"], "decreasing")

    def test_adaptive_budget_uses_three_recorded_expense_months(self):
        snapshot = fixture_snapshot()
        profile = build_financial_profile(snapshot)
        budget = build_adaptive_budget(snapshot, profile)
        food = next(row for row in budget["category_budgets"] if row["category"] == "Food")
        self.assertEqual(food["basis_months"], 3)
        self.assertEqual(food["current_spending"], Decimal("15000.00"))
        self.assertEqual(food["historical_average"], Decimal("11000.00"))
        self.assertEqual(food["recommended_amount"], Decimal("11000.00"))
        self.assertEqual(food["potential_monthly_improvement"], Decimal("4000.00"))

        short_history = fixture_snapshot()
        short_history["expenses"] = short_history["expenses"][-2:]
        short_history["incomes"] = short_history["incomes"][-1:]
        short_history["overview"] = build_intelligence_overview(short_history["incomes"], short_history["expenses"], user_id=1, as_of=date.today())
        short_budget = build_adaptive_budget(short_history, build_financial_profile(short_history))
        self.assertFalse(short_budget["baseline_available"])
        self.assertIsNone(short_budget["potential_monthly_improvement"])
        self.assertTrue(all(row["recommended_amount"] is None for row in short_budget["category_budgets"]))

    def test_goal_math_optimization_and_personalized_recommendations_have_supporting_metrics(self):
        goal = SimpleNamespace(
            id=1,
            name="Emergency reserve",
            target_amount=Decimal("70000"),
            current_amount=Decimal("20000"),
            target_date=date.today() + timedelta(days=180),
            priority="high",
            category="Emergency fund",
            status="active",
        )
        snapshot = fixture_snapshot([goal])
        profile = build_financial_profile(snapshot)
        behavior = build_behavior_analysis(snapshot, profile)
        budget = build_adaptive_budget(snapshot, profile)
        plan = build_goal_plan(snapshot, profile)
        summary = plan["goals"][0]
        self.assertEqual(summary["remaining_amount"], Decimal("50000.00"))
        self.assertEqual(summary["required_monthly_savings"], Decimal("8333.33"))
        self.assertIsNotNone(summary["projected_completion_date"])
        self.assertEqual(plan["optimization"]["allocations"][0]["goal_name"], "Emergency reserve")
        recommendations = build_personalized_recommendations(snapshot, profile, behavior, budget, plan)
        category_action = next(row for row in recommendations["recommendations"] if row["title"] == "Review Food spending")
        self.assertEqual(category_action["supporting_metric"]["current_spending"], Decimal("15000.00"))
        self.assertEqual(category_action["estimated_impact"]["monthly_cash_flow"], Decimal("4000.00"))

    def test_scenario_reduces_expense_without_mutating_records(self):
        snapshot = fixture_snapshot()
        change = ScenarioChange.model_validate({"change_type": "reduce_expense_category", "category": "Food", "amount": 2000})
        result = simulate_scenario(snapshot, [change], name="Food adjustment")
        self.assertEqual(result["status"], "SCENARIO")
        self.assertEqual(result["comparison"]["monthly_surplus_change"], Decimal("2000.00"))
        self.assertEqual(result["comparison"]["annual_surplus_change_if_repeated"], Decimal("24000.00"))
        self.assertEqual(result["proposed_plan"]["category_spending"]["Food"], Decimal("13000.00"))
        self.assertEqual(sum(row.amount for row in snapshot["expenses"] if row.date.month == date.today().month and row.category == "Food"), Decimal("15000"))

    def test_scenario_supports_income_recurring_budget_savings_and_goal_changes(self):
        snapshot = fixture_snapshot()
        income_change = ScenarioChange.model_validate({"change_type": "increase_income", "amount": 1000})
        self.assertEqual(simulate_scenario(snapshot, [income_change])["comparison"]["monthly_surplus_change"], Decimal("1000.00"))

        recurring_change = ScenarioChange.model_validate({"change_type": "decrease_recurring_expense", "category": "Rent", "amount": 500})
        recurring_result = simulate_scenario(snapshot, [recurring_change])
        self.assertEqual(recurring_result["comparison"]["monthly_surplus_change"], Decimal("500.00"))

        added_cost = ScenarioChange.model_validate({"change_type": "add_recurring_expense", "category": "Utilities", "amount": 600})
        self.assertEqual(simulate_scenario(snapshot, [added_cost])["comparison"]["monthly_surplus_change"], Decimal("-600.00"))

        savings_change = ScenarioChange.model_validate({"change_type": "increase_savings", "amount": 1500})
        savings_result = simulate_scenario(snapshot, [savings_change])
        self.assertEqual(savings_result["proposed_plan"]["planned_monthly_savings_allocation"], Decimal("1500.00"))
        self.assertEqual(savings_result["comparison"]["monthly_surplus_change"], Decimal("0.00"))

        budget_change = ScenarioChange.model_validate({"change_type": "change_budget", "category": "Food", "amount": 13000})
        self.assertEqual(simulate_scenario(snapshot, [budget_change])["comparison"]["monthly_surplus_change"], Decimal("2000.00"))

        goal = SimpleNamespace(id=44, name="Laptop", target_amount=Decimal("15000"), current_amount=Decimal("5000"), target_date=date.today() + timedelta(days=120), priority="medium", category="Equipment", status="active")
        snapshot["goals"] = [goal]
        goal_change = ScenarioChange.model_validate({"change_type": "change_goal_contribution", "goal_id": 44, "amount": 1000})
        goal_result = simulate_scenario(snapshot, [goal_change])
        self.assertEqual(goal_result["proposed_plan"]["goal_completion"][0]["scenario_monthly_contribution"], Decimal("1000.00"))
        self.assertEqual(goal_result["proposed_plan"]["goal_completion"][0]["projected_months_to_target"], 10)


class PersonalizationApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        database_path = Path(self.directory.name) / "personalization.db"
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "personalization-test-session-secret-012345",
            "SESSION_COOKIE_SECURE": False,
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "FRONTEND_URL": "http://localhost:5173",
        })
        create_tables(self.app)
        self.client_a = self.app.test_client()
        self.client_b = self.app.test_client()
        self.headers_a, self.user_a_id = self._register(self.client_a, "personal-a@example.test")
        self.headers_b, self.user_b_id = self._register(self.client_b, "personal-b@example.test")

    def tearDown(self):
        get_engine(self.app).dispose()
        self.directory.cleanup()

    def _register(self, client, email):
        response = client.post("/api/auth/register", json={"name": "Personal test", "email": email, "password": "Personal-test-password-123!"})
        self.assertEqual(response.status_code, 201, response.get_json())
        result = response.get_json()["data"]
        return {"X-CSRF-Token": result["csrf_token"]}, result["user"]["id"]

    def _add_finance(self, client, headers):
        today = date.today().replace(day=min(5, date.today().day))
        income = client.post("/api/income", headers=headers, json={"source": "Salary", "amount": 50000, "income_type": "Salary", "date": today.isoformat()})
        expense = client.post("/api/expenses", headers=headers, json={"category": "Food", "amount": 5000, "expense_type": "Essential", "date": today.isoformat()})
        self.assertEqual(income.status_code, 201, income.get_json())
        self.assertEqual(expense.status_code, 201, expense.get_json())

    def test_all_personalization_reads_require_authentication(self):
        anonymous = self.app.test_client()
        for endpoint in ("profile", "behavior", "budget", "goals", "recommendations", "insights"):
            response = anonymous.get(f"/api/personalization/{endpoint}")
            self.assertEqual(response.status_code, 401, endpoint)

    def test_profile_goals_and_recommendations_are_isolated(self):
        self._add_finance(self.client_a, self.headers_a)
        unauth = self.client_a.get("/api/personalization/profile?user_id=999999")
        self.assertEqual(unauth.status_code, 403)

        created = self.client_a.post("/api/personalization/goals", headers=self.headers_a, json={
            "name": "Course fund",
            "target_amount": 20000,
            "current_amount": 1000,
            "target_date": (date.today() + timedelta(days=120)).isoformat(),
            "priority": "high",
            "category": "Education",
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        goal_id = created.get_json()["data"]["goals"][0]["id"]
        self.assertEqual(self.client_b.get("/api/personalization/goals").get_json()["data"]["goals"], [])
        self.assertEqual(self.client_b.get(f"/api/personalization/profile?user_id={self.user_a_id}").status_code, 403)

        wrong_user_body = self.client_b.post("/api/personalization/goals", headers=self.headers_b, json={
            "user_id": self.user_a_id,
            "name": "Intruder goal",
            "target_amount": 1000,
            "target_date": (date.today() + timedelta(days=30)).isoformat(),
        })
        self.assertEqual(wrong_user_body.status_code, 403)
        self.assertEqual(self.client_b.put(f"/api/personalization/goals/{goal_id}", headers=self.headers_b, json={"name": "Taken over"}).status_code, 404)
        self.assertEqual(self.client_b.delete(f"/api/personalization/goals/{goal_id}", headers=self.headers_b).status_code, 404)
        wrong_goal_scenario = self.client_b.post("/api/personalization/what-if", headers=self.headers_b, json={
            "changes": [{"change_type": "change_goal_contribution", "goal_id": goal_id, "amount": 100}],
        })
        self.assertEqual(wrong_goal_scenario.status_code, 404)

        profile = self.client_a.get("/api/personalization/profile").get_json()["data"]
        self.assertEqual(profile["income_month_count"], 1)
        self.assertEqual(profile["average_monthly_income"], 50000)
        self.assertEqual(profile["average_monthly_surplus"], 45000)
        updated = self.client_a.put(f"/api/personalization/goals/{goal_id}", headers=self.headers_a, json={"current_amount": 5000, "priority": "medium"})
        self.assertEqual(updated.status_code, 200, updated.get_json())
        self.assertAlmostEqual(updated.get_json()["data"]["goals"][0]["progress_percent"], 25.0)
        with self.app.app_context(), session_scope() as db:
            changes = db.query(GoalContribution).filter_by(goal_id=goal_id).all()
            self.assertEqual(len(changes), 2)
            self.assertEqual(changes[-1].change_type, "contribution")
        deleted = self.client_a.delete(f"/api/personalization/goals/{goal_id}", headers=self.headers_a)
        self.assertEqual(deleted.status_code, 200)

    def test_what_if_and_scenario_endpoints_are_read_only_and_assistant_uses_engine(self):
        self._add_finance(self.client_a, self.headers_a)
        before = self.client_a.get("/api/expenses").get_json()["data"]
        plan = {"name": "Food trim", "changes": [{"change_type": "reduce_expense_category", "category": "Food", "amount": 1000}]}
        what_if = self.client_a.post("/api/personalization/what-if", headers=self.headers_a, json=plan)
        self.assertEqual(what_if.status_code, 200, what_if.get_json())
        self.assertEqual(what_if.get_json()["data"]["status"], "SCENARIO")
        self.assertEqual(what_if.get_json()["data"]["proposed_plan"]["expenses"], 4000)
        comparison = self.client_a.post("/api/personalization/scenario", headers=self.headers_a, json={"changes": [{"change_type": "increase_income", "amount": 2000}]})
        self.assertEqual(comparison.status_code, 200, comparison.get_json())
        self.assertEqual(comparison.get_json()["data"]["comparison"]["monthly_surplus_change"], 2000)
        invalid = self.client_a.post("/api/personalization/what-if", headers=self.headers_a, json={"changes": [{"change_type": "reduce_expense_category", "category": "Food", "amount": 8000}]})
        self.assertEqual(invalid.status_code, 400)
        after = self.client_a.get("/api/expenses").get_json()["data"]
        self.assertEqual(before, after)

        assistant = self.client_a.post("/api/assistant/chat", headers=self.headers_a, json={"question": "What if I reduce Food by ₹1,000?"})
        self.assertEqual(assistant.status_code, 200, assistant.get_json())
        facts = assistant.get_json()["data"]["factual_calculation"]
        self.assertEqual(assistant.get_json()["data"]["intent"], "SCENARIO")
        self.assertEqual(facts["status"], "SCENARIO")
        self.assertEqual(self.client_a.get("/api/expenses").get_json()["data"], before)

    def test_invalid_goal_scenario_and_empty_history_are_honest(self):
        insights = self.client_a.get("/api/personalization/insights")
        self.assertEqual(insights.status_code, 200, insights.get_json())
        self.assertFalse(insights.get_json()["data"]["profile"]["available"])
        self.assertEqual(insights.get_json()["data"]["behavior"]["behavioral_classification"]["label"], "Insufficient data")
        today = date.today()
        invalid_date = self.client_a.post("/api/personalization/goals", headers=self.headers_a, json={"name": "Past", "target_amount": 100, "target_date": today.isoformat()})
        self.assertEqual(invalid_date.status_code, 400)
        invalid_amount = self.client_a.post("/api/personalization/goals", headers=self.headers_a, json={"name": "Zero", "target_amount": 0, "target_date": (today + timedelta(days=10)).isoformat()})
        self.assertEqual(invalid_amount.status_code, 400)
        self.assertEqual(self.client_a.post("/api/personalization/scenario", headers=self.headers_a, json={"changes": []}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
