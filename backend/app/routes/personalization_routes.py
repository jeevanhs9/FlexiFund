"""Authenticated, account-scoped Phase 7 personalization APIs."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.auth import authenticated_blueprint, authenticated_user_id, authorize_body_user_id, authorize_user_id
from app.database import session_scope
from app.models import FinancialGoal, GoalContribution
from app.routes.helpers import error_response, json_amount, parse_json_body, success_response
from app.schemas import FinancialGoalCreate, FinancialGoalUpdate, ScenarioPlan
from app.services.adaptive_budget import build_adaptive_budget
from app.services.behavior_analyzer import build_behavior_analysis
from app.services.financial_profile import build_financial_profile
from app.services.goal_engine import build_goal_plan
from app.services.personalization_service import load_personalization_snapshot
from app.services.personalized_recommendations import build_personalized_recommendations
from app.services.scenario_engine import simulate_scenario


personalization_bp = authenticated_blueprint(
    Blueprint("personalization", __name__, url_prefix="/api/personalization")
)


def _json_safe(value: Any, key: str = "") -> Any:
    if isinstance(value, Decimal):
        if any(part in key.casefold() for part in ("rate", "ratio", "percent", "change", "score")):
            return float(value)
        return json_amount(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(child_key): _json_safe(child, str(child_key)) for child_key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(child, key) for child in value]
    return value


def _user_id_from_query():
    return authorize_user_id(request.args.get("user_id"))


def _components(database_session, user_id: int) -> dict:
    snapshot = load_personalization_snapshot(database_session, user_id)
    profile = build_financial_profile(snapshot)
    behavior = build_behavior_analysis(snapshot, profile)
    budget = build_adaptive_budget(snapshot, profile)
    goals = build_goal_plan(snapshot, profile)
    recommendations = build_personalized_recommendations(snapshot, profile, behavior, budget, goals)
    return {
        "profile": profile,
        "behavior": behavior,
        "budget": budget,
        "goals": goals,
        "recommendations": recommendations,
        "risk": snapshot["overview"]["risk"],
        "insights": {
            "available": profile["available"],
            "behavioral_classification": behavior["behavioral_classification"],
            "top_behavioral_insights": behavior["insights"][:6],
            "risk_factors": snapshot["overview"]["risk"]["risk_factors"],
            "personalized_actions": recommendations["recommendations"][:5],
            "insufficient_data": sorted(set(profile["insufficient_data"] + behavior["insufficient_data"] + budget["insufficient_data"] + recommendations["insufficient_data"])),
        },
    }


def _read(component: str | None = None):
    user_id, error = _user_id_from_query()
    if error:
        return error
    try:
        with session_scope() as database_session:
            data = _components(database_session, user_id)
    except SQLAlchemyError:
        return error_response("Personalized financial data is temporarily unavailable.", 503)
    return jsonify({"status": "success", "data": _json_safe(data if component is None else data[component])})


def _goal_owner_query(database_session, user_id: int, goal_id: int):
    return database_session.scalar(
        select(FinancialGoal).where(FinancialGoal.id == goal_id, FinancialGoal.user_id == user_id)
    )


def _record_goal_adjustment(database_session, goal: FinancialGoal, previous: Decimal, current: Decimal):
    difference = current - previous
    if difference == 0:
        return
    database_session.add(
        GoalContribution(
            goal_id=goal.id,
            user_id=goal.user_id,
            amount=abs(difference),
            change_type="contribution" if difference > 0 else "withdrawal",
            contributed_at=date.today(),
        )
    )


@personalization_bp.get("/insights")
def get_insights():
    return _read()


@personalization_bp.get("/profile")
def get_profile():
    return _read("profile")


@personalization_bp.get("/behavior")
def get_behavior():
    return _read("behavior")


@personalization_bp.get("/budget")
def get_budget():
    return _read("budget")


@personalization_bp.get("/goals")
def get_goals():
    return _read("goals")


@personalization_bp.get("/recommendations")
def get_recommendations():
    return _read("recommendations")


@personalization_bp.post("/goals")
def create_goal():
    body, error = parse_json_body(FinancialGoalCreate)
    if error:
        return error_response(error)
    user_id = authenticated_user_id()
    user_error = authorize_body_user_id(body.user_id)
    if user_error:
        return user_error
    if body.current_amount > body.target_amount:
        return error_response("current_amount cannot exceed target_amount.")
    try:
        with session_scope() as database_session:
            goal = FinancialGoal(
                user_id=user_id,
                name=body.name,
                target_amount=body.target_amount,
                current_amount=body.current_amount,
                target_date=body.target_date,
                priority=body.priority,
                category=body.category,
                status="completed" if body.current_amount >= body.target_amount else "active",
            )
            database_session.add(goal)
            database_session.flush()
            if body.current_amount > 0:
                database_session.add(
                    GoalContribution(
                        goal_id=goal.id,
                        user_id=user_id,
                        amount=body.current_amount,
                        change_type="opening_balance",
                        contributed_at=date.today(),
                    )
                )
            data = _components(database_session, user_id)["goals"]
    except SQLAlchemyError:
        return error_response("The financial goal could not be saved.", 503)
    return success_response(_json_safe(data), 201)


@personalization_bp.put("/goals/<int:goal_id>")
def update_goal(goal_id: int):
    body, error = parse_json_body(FinancialGoalUpdate)
    if error:
        return error_response(error)
    user_id = authenticated_user_id()
    user_error = authorize_body_user_id(body.user_id)
    if user_error:
        return user_error
    try:
        with session_scope() as database_session:
            goal = _goal_owner_query(database_session, user_id, goal_id)
            if goal is None:
                return error_response("Financial goal was not found.", 404)
            updates = body.model_dump(exclude_unset=True, exclude={"user_id"})
            new_target = updates.get("target_amount", goal.target_amount)
            new_current = updates.get("current_amount", goal.current_amount)
            if new_current > new_target:
                return error_response("current_amount cannot exceed target_amount.")
            previous_current = goal.current_amount
            for field, value in updates.items():
                setattr(goal, field, value)
            if goal.current_amount >= goal.target_amount:
                goal.status = "completed"
            elif goal.status == "completed":
                goal.status = "active"
            _record_goal_adjustment(database_session, goal, previous_current, goal.current_amount)
            database_session.flush()
            data = _components(database_session, user_id)["goals"]
    except SQLAlchemyError:
        return error_response("The financial goal could not be updated.", 503)
    return success_response(_json_safe(data))


@personalization_bp.delete("/goals/<int:goal_id>")
def delete_goal(goal_id: int):
    try:
        with session_scope() as database_session:
            goal = _goal_owner_query(database_session, authenticated_user_id(), goal_id)
            if goal is None:
                return error_response("Financial goal was not found.", 404)
            database_session.delete(goal)
            database_session.flush()
    except SQLAlchemyError:
        return error_response("The financial goal could not be deleted.", 503)
    return success_response({"deleted": True, "goal_id": goal_id})


def _run_scenario():
    body, error = parse_json_body(ScenarioPlan)
    if error:
        return None, error_response(error)
    user_error = authorize_body_user_id(body.user_id)
    if user_error:
        return None, user_error
    try:
        with session_scope() as database_session:
            snapshot = load_personalization_snapshot(database_session, authenticated_user_id())
            result = simulate_scenario(snapshot, body.changes, name=body.name)
    except LookupError:
        return None, error_response("Financial goal was not found.", 404)
    except ValueError as exc:
        return None, error_response(str(exc), 400)
    except SQLAlchemyError:
        return None, error_response("Scenario data is temporarily unavailable.", 503)
    return result, None


@personalization_bp.post("/what-if")
def what_if():
    result, error = _run_scenario()
    if error:
        return error
    return success_response(_json_safe(result))


@personalization_bp.post("/scenario")
def compare_scenario():
    result, error = _run_scenario()
    if error:
        return error
    return success_response(_json_safe(result))
