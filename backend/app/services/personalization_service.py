"""Load one authenticated user's data and reuse the Phase 5 analysis pipeline."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Expense, FinancialGoal, GoalContribution, Income
from app.services.intelligence_service import build_intelligence_overview


def load_personalization_snapshot(database_session: Session, user_id: int) -> dict:
    """Fetch scoped finance rows, goals and contributions once for a request."""
    incomes = database_session.scalars(
        select(Income).where(Income.user_id == user_id).order_by(Income.date, Income.id)
    ).all()
    expenses = database_session.scalars(
        select(Expense).where(Expense.user_id == user_id).order_by(Expense.date, Expense.id)
    ).all()
    goals = database_session.scalars(
        select(FinancialGoal)
        .where(FinancialGoal.user_id == user_id)
        .order_by(FinancialGoal.target_date, FinancialGoal.id)
    ).all()
    contributions = database_session.scalars(
        select(GoalContribution)
        .where(GoalContribution.user_id == user_id)
        .order_by(GoalContribution.contributed_at, GoalContribution.id)
    ).all()
    overview = build_intelligence_overview(incomes, expenses, user_id=user_id)
    return {
        "user_id": user_id,
        "incomes": incomes,
        "expenses": expenses,
        "goals": goals,
        "goal_contributions": contributions,
        "overview": overview,
    }
