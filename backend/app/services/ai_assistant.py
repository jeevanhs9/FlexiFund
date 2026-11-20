"""Orchestrate account-scoped intent, facts, Phase 5 analysis, and explanation."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import re

from sqlalchemy.orm import Session

from app.services.financial_context import build_financial_context
from app.services.llm_service import generate_explanation
from app.schemas import ScenarioChange, ScenarioPlan
from app.services.adaptive_budget import build_adaptive_budget
from app.services.behavior_analyzer import build_behavior_analysis
from app.services.financial_profile import build_financial_profile
from app.services.goal_engine import build_goal_plan
from app.services.personalization_service import load_personalization_snapshot
from app.services.personalized_recommendations import build_personalized_recommendations
from app.services.query_analyzer import Intent, analyze_question
from app.services.response_generator import generate_verified_response
from app.services.scenario_engine import simulate_scenario


def _plain(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(child) for child in value]
    return value


def _scenario_change(question: str, category: str | None):
    text = question.casefold()
    match = re.search(r"(?:₹|rs\.?\s*|inr\s*)?(\d[\d,]*(?:\.\d{1,2})?)\s*(k)?\b", text)
    if not match:
        return None, "Include a monthly amount, such as ₹2,000, so I can calculate the scenario."
    amount = Decimal(match.group(1).replace(",", "")) * (1000 if match.group(2) else 1)
    if amount <= 0:
        return None, "The scenario amount must be greater than zero."
    if re.search(r"\b(increase|raise|add)\b.*\bincome\b|\bincome\b.*\b(increase|raise)\b", text):
        values = {"change_type": "increase_income", "amount": amount}
    elif re.search(r"\b(sav(e|ings)|contribution)\b", text) and re.search(r"\b(increase|save|add)\b", text):
        values = {"change_type": "increase_savings", "amount": amount}
    elif "recurring" in text and re.search(r"\b(reduce|cut|lower|decrease)\b", text):
        if not category:
            return None, "Name an expense category so I can check detected recurring costs."
        values = {"change_type": "decrease_recurring_expense", "category": category, "amount": amount}
    elif re.search(r"\b(budget)\b", text) and category:
        values = {"change_type": "change_budget", "category": category, "amount": amount}
    elif re.search(r"\b(reduce|cut|lower|decrease)\b", text):
        if not category:
            return None, "Name an expense category so I can calculate the spending change."
        values = {"change_type": "reduce_expense_category", "category": category, "amount": amount}
    else:
        return None, "Specify whether you want to reduce a category, change a budget, increase income, or allocate more to savings."
    try:
        return ScenarioPlan.model_validate({"changes": [values]}).changes, None
    except Exception:
        return None, "The question did not include a supported scenario change."


def _build_personalized_response(database_session: Session, *, user_id: int, intent: Intent, question: str, category: str | None):
    snapshot = load_personalization_snapshot(database_session, user_id)
    profile = build_financial_profile(snapshot)
    behavior = build_behavior_analysis(snapshot, profile)
    budget = build_adaptive_budget(snapshot, profile)
    goals = build_goal_plan(snapshot, profile)
    recommendations = build_personalized_recommendations(snapshot, profile, behavior, budget, goals)
    text = question.casefold()

    if intent == Intent.SCENARIO:
        changes, issue = _scenario_change(question, category)
        if issue:
            facts = {"scenario_available": False, "reason": issue}
            return {"answer": issue, "facts": facts}
        try:
            result = simulate_scenario(snapshot, changes, name="Assistant what-if")
        except (ValueError, LookupError) as error:
            answer = str(error)
            return {"answer": answer, "facts": {"scenario_available": False, "reason": answer}}
        proposed = result["proposed_plan"]
        improvement = result["comparison"]["monthly_surplus_change"]
        answer = (
            f"SCENARIO: monthly expenses would be ₹{proposed['expenses']:,.2f}, "
            f"monthly surplus would be ₹{proposed['surplus']:,.2f}, and the change in surplus would be ₹{improvement:,.2f}. "
            f"If that monthly difference repeated for 12 months, the projected annual surplus change is "
            f"₹{result['comparison']['annual_surplus_change_if_repeated']:,.2f}. This does not change your records."
        )
        return {"answer": answer, "facts": _plain(result)}

    if intent == Intent.GOAL:
        active = [goal for goal in goals["goals"] if goal["status"] == "active"]
        facts = _plain({"goals": goals, "risk_band": snapshot["overview"]["risk"]["band"]})
        if not active:
            return {"answer": "There is no saved personal savings goal for this account yet. Create a goal to calculate its remaining amount, monthly requirement, and projected completion. Current income and expense history can still help estimate a contribution capacity.", "facts": facts}
        lines = [
            f"{goal['name']}: ₹{goal['remaining_amount']:,.2f} remaining; about ₹{goal['required_monthly_savings']:,.2f} per month through the target month; feasibility is {goal['feasibility'].replace('_', ' ')}."
            for goal in active[:4]
        ]
        allocations = goals["optimization"]["allocations"]
        first = allocations[0]["goal_name"] if allocations else None
        priority_line = f" The current explainable ordering starts with {first} based on priority and deadline." if first else ""
        return {"answer": " ".join(lines) + priority_line + " These are planning estimates based on observed surplus, not a guarantee.", "facts": facts}

    if intent == Intent.BUDGET:
        facts = _plain({"adaptive_budget": budget, "financial_health": snapshot["overview"]["risk"]})
        actionable = [row for row in budget["category_budgets"] if row["potential_monthly_improvement"] is not None and row["potential_monthly_improvement"] > 0]
        if actionable:
            rows = [f"{row['category']}: current ₹{row['current_spending']:,.2f}, observed average ₹{row['historical_average']:,.2f}, suggested ceiling ₹{row['recommended_amount']:,.2f}, potential improvement ₹{row['potential_monthly_improvement']:,.2f}." for row in actionable[:3]]
            answer = "Based on your recorded history: " + " ".join(rows)
        else:
            answer = budget["insufficient_data"][0] if budget["insufficient_data"] else "The recorded categories do not support a lower budget target for this month."
        return {"answer": answer, "facts": facts}

    if intent == Intent.RECOMMENDATION:
        facts = _plain({"recommendations": recommendations, "behavioral_insights": behavior["insights"][:5]})
        if re.search(r"hurting .* savings|most .* savings", text):
            current_categories = snapshot["overview"]["spending"]["categories"]
            if current_categories:
                top = current_categories[0]
                answer = f"{top['category']} is your largest recorded expense category this month at ₹{top['amount']:,.2f}. That is a spending comparison, not proof that it caused lower savings."
                facts["largest_current_category"] = _plain(top)
                return {"answer": answer, "facts": facts}
        items = recommendations["recommendations"][:3]
        if items:
            answer = "Based on your recorded data: " + " ".join(f"{row['title']}: {row['explanation']}" for row in items)
        else:
            answer = recommendations["insufficient_data"][0]
        return {"answer": answer, "facts": facts}

    if intent == Intent.RISK:
        risk = snapshot["overview"]["risk"]
        facts = _plain({
            "financial_health": risk,
            "health_score": risk["score"],
            "health_band": risk["band"],
            "coverage_percent": risk["coverage_percent"],
            "risk_factors": risk["risk_factors"],
            "savings_rate_trend": behavior["savings_rate_trend"],
            "monthly_expense_trend": behavior["monthly_expense_trend"],
            "risk_actions": recommendations["recommendations"][:5],
        })
        if risk["score"] is None:
            answer = "There isn't enough recorded history to calculate a financial health score yet."
        else:
            factors = "; ".join(row["message"] for row in risk["risk_factors"][:4]) or "No high-severity factor was found in the recorded data."
            answer = f"Your Phase 5 indicator is {risk['score']}/100 ({risk['band']}, {risk['coverage_percent']:.0f}% component coverage). The recorded factors are: {factors} This is a budgeting indicator, not a credit score."
            trend = behavior["savings_rate_trend"]
            if trend["status"] == "declining":
                answer += " The latest consecutive observed months also show a declining savings rate."
        return {"answer": answer, "facts": facts}

    if intent == Intent.SAVINGS and ("every month" in text or "monthly" in text or "goal" in text):
        active = [goal for goal in goals["goals"] if goal["status"] == "active"]
        if active:
            facts = _plain({"goals": goals})
            answer = " ".join(f"For {goal['name']}, the calculated requirement is about ₹{goal['required_monthly_savings']:,.2f} per month." for goal in active[:4])
            answer += " The allocation plan compares these requirements with observed positive surplus and is not guaranteed."
            return {"answer": answer, "facts": facts}
        if profile["average_monthly_surplus"] is not None:
            answer = f"Your average recorded monthly surplus is ₹{profile['average_monthly_surplus']:,.2f}, based on {profile['cash_flow_month_count']} month(s) where both income and expenses were recorded. That is a reference for planning, not a guaranteed safe savings target."
        else:
            answer = profile["insufficient_data"][-1] if profile["insufficient_data"] else "There isn't enough same-month income and expense data to estimate monthly savings capacity yet."
        return {"answer": answer, "facts": _plain({"profile": profile, "goals": goals})}

    return None


def build_verified_response(
    database_session: Session,
    *,
    user_id: int,
    question: str,
) -> dict:
    """Create intent-specific facts and factual copy from the Phase 5 pipeline."""
    analysis = analyze_question(question)
    if analysis.intent in {Intent.SCENARIO, Intent.GOAL, Intent.BUDGET, Intent.RECOMMENDATION, Intent.RISK} or (
        analysis.intent == Intent.SAVINGS and re.search(r"\b(every month|monthly|goal)\b", question.casefold())
    ):
        personalized = _build_personalized_response(
            database_session,
            user_id=user_id,
            intent=analysis.intent,
            question=question,
            category=analysis.category,
        )
        if personalized is not None:
            verified = {"intent": analysis.intent.value, "facts": personalized["facts"], "factual_answer": personalized["answer"], "question": question}
            return verified
    context = build_financial_context(database_session, user_id, analysis)
    verified = generate_verified_response(analysis.intent, context, category=analysis.category)
    return {
        "intent": analysis.intent.value,
        "facts": verified["facts"],
        "factual_answer": verified["answer"],
        "question": question,
    }


def add_explanation(verified: dict, *, history: list[dict] | None = None) -> dict:
    """Attach an optional provider explanation after the DB read transaction ends."""
    llm_result = generate_explanation(
        question=verified["question"],
        facts=verified["facts"],
        history=history or [],
    )
    explanation = llm_result["text"]
    answer = verified["factual_answer"]
    stored_message = f"[FACTUAL CALCULATION]\n{answer}"
    if explanation:
        stored_message = f"{stored_message}\n\n[AI-GENERATED EXPLANATION]\n{explanation}"
    return {
        "intent": verified["intent"],
        "factual_calculation": verified["facts"],
        "factual_answer": verified["factual_answer"],
        "ai_explanation": explanation,
        "answer": answer,
        "explanation_source": "ai" if explanation else "deterministic_fallback",
        "ai_status": llm_result["status"],
        "stored_message": stored_message,
    }
