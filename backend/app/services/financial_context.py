"""Fetch a user's rows and reduce Phase 5 results to intent-specific context."""

from __future__ import annotations

from calendar import month_name
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Expense, Income
from app.services.intelligence_service import build_intelligence_overview
from app.services.query_analyzer import Intent, QueryAnalysis


def _number(value):
    if value is None:
        return None
    return float(value) if isinstance(value, Decimal) else value


def _summary(overview: dict) -> dict:
    values = overview["summary"]
    period = overview["period"]
    month = period.get("month")
    year = period.get("year")
    return {
        "period": f"{month_name[month]} {year}" if month and year else str(year or "all recorded months"),
        "month": month,
        "year": year,
        "income": _number(values["total_income"]),
        "expenses": _number(values["total_expenses"]),
        "surplus": _number(values["surplus"]),
        "savings_rate_percent": _number(values["savings_rate"]),
        "expense_ratio_percent": _number(values["expense_ratio"]),
        "essential_expenses": _number(values["essential_expenses"]),
        "non_essential_expenses": _number(values["non_essential_expenses"]),
        "recorded_transactions": overview["data_quality"]["valid_rows"],
        "observed_months": len(overview["features"]["monthly_history"]),
    }


def build_financial_context(
    database_session: Session,
    user_id: int,
    analysis: QueryAnalysis,
) -> dict:
    """Run the existing intelligence pipeline on this user's actual records.

    Only summarized metrics relevant to the detected intent leave this service.
    Transaction descriptions, account details, and unrelated history are omitted.
    """
    incomes = database_session.scalars(
        select(Income).where(Income.user_id == user_id).order_by(Income.date, Income.id)
    ).all()
    expenses = database_session.scalars(
        select(Expense).where(Expense.user_id == user_id).order_by(Expense.date, Expense.id)
    ).all()
    overview = build_intelligence_overview(incomes, expenses, user_id=user_id)
    intent = analysis.intent
    context = {
        "period_summary": _summary(overview),
        "has_financial_history": overview["data_quality"]["valid_rows"] > 0,
    }

    if intent in {Intent.EXPENSE, Intent.SPENDING, Intent.CATEGORY, Intent.BUDGET, Intent.ANOMALY}:
        categories = overview["spending"]["categories"]
        if analysis.category:
            categories = [row for row in categories if row["category"] == analysis.category]
        context["categories"] = [
            {
                "category": row["category"],
                "amount": _number(row["amount"]),
                "share_percent": _number(row["percentage"]),
                "transaction_count": row["transaction_count"],
            }
            for row in categories[:5]
        ]
        context["category_trends"] = [
            {
                "category": row["category"],
                "trend": row["trend"],
                "current_amount": _number(row["current_amount"]),
                "previous_amount": _number(row["previous_amount"]),
                "change_percent": _number(row["percentage_change"]),
            }
            for row in overview["spending"]["category_trends"]
            if not analysis.category or row["category"] == analysis.category
        ][:5]

    if intent in {Intent.SAVINGS, Intent.FORECAST, Intent.ANOMALY}:
        forecast = overview["forecast"]
        context["forecast"] = {
            "available": forecast["available"],
            "forecast_month": forecast["forecast_month"],
            "forecast_period": forecast["forecast_period"],
            "predicted_income": _number(forecast["predicted_income"]),
            "predicted_expenses": _number(forecast["predicted_expenses"]),
            "predicted_savings": _number(forecast["predicted_savings"]),
            "historical_months": forecast["historical_months"],
            "confidence": forecast["confidence"],
            "explanation": forecast["explanation"],
        }
        savings = overview["savings"]
        context["savings"] = {
            "average_monthly_savings": _number(savings["average_monthly_savings"]),
            "current_savings_rate_percent": _number(savings["current_savings_rate"]),
            "predicted_savings_rate_percent": _number(savings["predicted_savings_rate"]),
            "trend": savings["savings_trend"],
            "available": savings["available"],
        }
        expense_prediction = overview["expense_prediction"]
        context["expense_prediction"] = {
            "available": expense_prediction["available"],
            "predicted_expenses": _number(expense_prediction["predicted_expenses"]),
            "forecast_period": expense_prediction["forecast_period"],
            "selected_model": expense_prediction["selected_model"],
            "historical_months": expense_prediction["historical_months"],
            "predicted_change_from_latest": _number(expense_prediction.get("predicted_change_from_latest")),
            "predicted_change_percent": _number(expense_prediction.get("predicted_change_percent")),
            "evaluation": expense_prediction.get("evaluation"),
            "explanation": expense_prediction["explanation"],
        }

    if intent in {Intent.RISK, Intent.FINANCIAL_HEALTH, Intent.RECOMMENDATION, Intent.GENERAL}:
        risk = overview["risk"]
        context["financial_health"] = {
            "score": risk["score"],
            "band": risk["band"],
            "coverage_percent": risk["coverage_percent"],
            "explanation": risk["explanation"],
            "risk_factors": [
                {"factor": row["factor"], "severity": row["severity"], "message": row["message"]}
                for row in risk["risk_factors"][:5]
            ],
        }

    if intent in {Intent.ANOMALY, Intent.RECOMMENDATION}:
        context["category_trends"] = [
            {
                "category": row["category"],
                "trend": row["trend"],
                "current_amount": _number(row["current_amount"]),
                "previous_amount": _number(row["previous_amount"]),
                "change_percent": _number(row["percentage_change"]),
            }
            for row in overview["spending"]["category_trends"]
            if not analysis.category or row["category"] == analysis.category
        ][:5]
        context["anomalies"] = [
            {
                "category": row["category"],
                "period": row["period"],
                "current_amount": _number(row["current_amount"]),
                "historical_average": _number(row["historical_average"]),
                "increase_percent": _number(row.get("increase_percentage")),
                "explanation": row["explanation"],
            }
            for row in overview["anomalies"][:5]
        ]

    if intent == Intent.RECOMMENDATION:
        context["recommendations"] = [
            {"priority": row["priority"], "title": row["title"], "message": row["message"], "basis": row["basis"]}
            for row in overview["recommendations"][:5]
        ]

    if intent == Intent.GOAL:
        emergency = overview["emergency_fund"]
        context["goal_support"] = {
            "available": overview["goals"]["available"],
            "message": overview["goals"]["message"],
            "emergency_fund_balance_configured": emergency["balance_configured"],
            "emergency_fund_minimum_target": _number(emergency["recommended_minimum"]),
            "emergency_fund_target": _number(emergency["recommended_target"]),
        }

    return context
