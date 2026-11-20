"""Orchestrate the data-to-insight pipeline for one explicitly selected user."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from flask import current_app, has_app_context

from app.services.anomaly_detection import detect_anomalies
from app.services.data_processor import prepare_transactions
from app.services.feature_engineering import engineer_features
from app.services.financial_engine import calculate_summary
from app.services.expense_prediction import predict_next_month_expenses
from app.services.forecasting_engine import apply_expense_prediction, forecast_cash_flow
from app.services.recommendation_engine import generate_recommendations
from app.services.recurring_detection import detect_recurring_expenses
from app.services.risk_engine import score_financial_risk
from app.services.savings_prediction import predict_savings
from app.services.spending_analysis import analyze_spending


def build_intelligence_overview(
    incomes: list,
    expenses: list,
    *,
    user_id: int,
    month: int | None = None,
    year: int | None = None,
    as_of: date | None = None,
) -> dict:
    """Run validation, feature engineering, calculations and explainable insights."""
    as_of = as_of or date.today()
    month = as_of.month if month is None and year is None else month
    year = as_of.year if year is None else year

    transactions, quality = prepare_transactions(incomes, expenses, user_id)
    historical_count = len(transactions)
    transactions = [row for row in transactions if row.date <= as_of]
    future_excluded = historical_count - len(transactions)
    if future_excluded:
        quality["future_dated_rows_excluded"] = future_excluded
        quality["warnings"].append(f"{future_excluded} future-dated row(s) were excluded from historical analysis.")

    selected = [
        row for row in transactions
        if row.date.year == year and (month is None or row.date.month == month)
    ]
    summary = calculate_summary(selected)
    features = engineer_features(transactions)
    monthly = features["monthly_history"]
    spending = analyze_spending(transactions, selected, monthly)
    model_store_dir = current_app.config.get("MODEL_STORE_DIR") if has_app_context() else None
    expense_prediction = predict_next_month_expenses(
        monthly, user_id=user_id, as_of=as_of, model_store_dir=model_store_dir
    )
    forecast = apply_expense_prediction(
        forecast_cash_flow(monthly, as_of=as_of), expense_prediction
    )
    savings = predict_savings(monthly, forecast)
    anomalies = detect_anomalies(transactions, selected)
    risk = score_financial_risk(monthly, spending, expense_prediction=expense_prediction)
    recommendations = generate_recommendations(summary, spending, forecast, risk, quality, anomalies)
    recurring = detect_recurring_expenses(transactions)

    essential_months = [row for row in monthly if row["essential_expenses"] > 0]
    if essential_months:
        basis_months = essential_months[-3:]
        essential_baseline = sum((row["essential_expenses"] for row in basis_months), start=0) / len(basis_months)
        emergency = {
            "current_balance": None,
            "balance_configured": False,
            "monthly_essential_expenses": essential_baseline,
            "basis_months": len(basis_months),
            "provisional": len(basis_months) < 3,
            "recommended_minimum": (essential_baseline * 3).quantize(Decimal("0.01")),
            "recommended_target": (essential_baseline * 6).quantize(Decimal("0.01")),
            "progress_percent": None,
            "message": "A current emergency-fund balance has not been provided. Targets use the average essential expenses in observed transaction months, which may be incomplete, and do not imply current savings.",
        }
    else:
        emergency = {
            "current_balance": None,
            "balance_configured": False,
            "monthly_essential_expenses": None,
            "basis_months": 0,
            "provisional": True,
            "recommended_minimum": None,
            "recommended_target": None,
            "progress_percent": None,
            "message": "Add essential expense records to estimate emergency-fund targets. A current balance has not been provided.",
        }

    return {
        "user_id": user_id,
        "period": {"month": month, "year": year},
        "data_quality": quality,
        "summary": summary,
        "features": features,
        "spending": spending,
        "forecast": forecast,
        "expense_prediction": expense_prediction,
        "savings": savings,
        "risk": risk,
        "anomalies": anomalies,
        "recurring": recurring,
        "recommendations": recommendations,
        "emergency_fund": emergency,
        "goals": {"available": False, "message": "Financial goals are not supported by the current database schema."},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
