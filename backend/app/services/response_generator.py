"""Build verified, deterministic answer content from summarized engine output."""

from __future__ import annotations

from decimal import Decimal

from app.services.query_analyzer import Intent


def _money(value) -> str:
    return f"₹{Decimal(str(value)):,.2f}"


def generate_verified_response(intent: Intent, context: dict, *, category: str | None = None) -> dict:
    """Return factual copy and a compact fact set; never invent missing values."""
    summary = context["period_summary"]
    period = summary["period"]
    facts: dict = {"period": period}
    if not context["has_financial_history"] and intent not in {Intent.FORECAST, Intent.GOAL}:
        return {
            "answer": "I don't have recorded income or expense data for your account yet. Add transactions before I calculate personal financial insights.",
            "facts": {"period": period, "recorded_transactions": 0},
        }

    if intent == Intent.BALANCE:
        surplus = summary["surplus"]
        facts.update({"recorded_income": summary["income"], "recorded_expenses": summary["expenses"], "recorded_surplus": surplus})
        result_label = "surplus" if surplus >= 0 else "deficit"
        return {
            "answer": f"I don't track a live bank balance. For {period}, recorded income is {_money(summary['income'])} and recorded expenses are {_money(summary['expenses'])}, leaving a recorded {result_label} of {_money(abs(surplus))}.",
            "facts": facts,
        }

    if intent == Intent.INCOME:
        facts["recorded_income"] = summary["income"]
        answer = (
            f"You recorded {_money(summary['income'])} in income for {period}."
            if summary["income"]
            else f"No income is recorded for {period}."
        )
        return {"answer": answer, "facts": facts}

    if intent in {Intent.EXPENSE, Intent.SPENDING, Intent.CATEGORY}:
        facts["recorded_expenses"] = summary["expenses"]
        categories = context.get("categories", [])
        if intent == Intent.CATEGORY and not categories:
            answer = f"No {category or 'matching category'} expenses are recorded for {period}."
        elif categories:
            facts["categories"] = categories
            top = categories[0]
            answer = (
                f"You recorded {_money(summary['expenses'])} in expenses for {period}. "
                f"{top['category']} is the largest listed category at {_money(top['amount'])} "
                f"({top['share_percent']:.1f}% of recorded expenses)."
            )
        else:
            answer = f"You recorded {_money(summary['expenses'])} in expenses for {period}."
        return {"answer": answer, "facts": facts}

    if intent == Intent.BUDGET:
        facts.update({"recorded_expenses": summary["expenses"], "categories": context.get("categories", [])})
        return {
            "answer": f"FlexiFund doesn't store a custom budget yet. For {period}, recorded expenses total {_money(summary['expenses'])}. The category totals below can help you choose a budget, but they are historical spending, not budget limits.",
            "facts": facts,
        }

    if intent == Intent.SAVINGS:
        facts.update({"recorded_surplus": summary["surplus"], "savings_rate_percent": summary["savings_rate_percent"]})
        if summary["income"] <= 0:
            answer = f"For {period}, recorded income is {_money(summary['income'])} and expenses are {_money(summary['expenses'])}. A savings rate can't be calculated without recorded income."
        else:
            answer = f"For {period}, recorded income minus expenses leaves {_money(summary['surplus'])}. The recorded savings rate is {summary['savings_rate_percent']:.1f}%."
        forecast = context.get("forecast", {})
        if forecast.get("available"):
            facts["predicted_next_month_savings"] = forecast["predicted_savings"]
            answer += f" The Phase 5 forecast estimates { _money(forecast['predicted_savings']) } in savings for {forecast['forecast_month']}."
        return {"answer": answer, "facts": facts}

    if intent == Intent.FORECAST:
        forecast = context.get("forecast", {})
        if not forecast.get("available"):
            facts.update({"forecast_available": False, "historical_months": forecast.get("historical_months", 0)})
            return {"answer": "I don't have enough historical financial data to calculate a reliable forecast yet. " + forecast.get("explanation", ""), "facts": facts}
        facts.update({
            "forecast_available": True,
            "forecast_month": forecast["forecast_month"],
            "predicted_income": forecast["predicted_income"],
            "predicted_expenses": forecast["predicted_expenses"],
            "predicted_savings": forecast["predicted_savings"],
            "historical_months": forecast["historical_months"],
            "confidence": forecast["confidence"],
        })
        expense_prediction = context.get("expense_prediction", {})
        if expense_prediction.get("available"):
            facts["expense_prediction"] = expense_prediction
            direction = "above" if expense_prediction["predicted_change_from_latest"] > 0 else "below" if expense_prediction["predicted_change_from_latest"] < 0 else "the same as"
            comparison = f" The expense model's estimate is {_money(abs(expense_prediction['predicted_change_from_latest']))} {direction} the latest recorded expense month."
        else:
            comparison = " " + expense_prediction.get("explanation", "")
        answer = (
            f"Using {forecast['historical_months']} completed months, FlexiFund estimates {forecast['forecast_month']} income at "
            f"{_money(forecast['predicted_income'])}, expenses at {_money(forecast['predicted_expenses'])}, and savings at "
            f"{_money(forecast['predicted_savings'])}. This is a statistical estimate, not a guarantee.{comparison}"
        )
        return {"answer": answer, "facts": facts}

    if intent in {Intent.RISK, Intent.FINANCIAL_HEALTH}:
        health = context.get("financial_health", {})
        score = health.get("score")
        facts.update({"health_score": score, "health_band": health.get("band"), "coverage_percent": health.get("coverage_percent"), "risk_factors": health.get("risk_factors", [])})
        if score is None:
            answer = "There isn't enough recorded history to calculate a financial health score yet. Add more income and expense records, then ask again."
        else:
            answer = f"Your current FlexiFund financial health indicator is {score}/100 ({health['band']}) using {health['coverage_percent']:.0f}% of the weighted components supported by your records. It is a budgeting indicator, not a credit score."
        return {"answer": answer, "facts": facts}

    if intent == Intent.ANOMALY:
        anomalies = context.get("anomalies", [])
        increasing = [row for row in context.get("category_trends", []) if row["trend"] == "increasing"]
        facts.update({"anomalies": anomalies, "increasing_categories": increasing})
        expense_prediction = context.get("expense_prediction", {})
        if expense_prediction.get("available"):
            facts["expense_prediction"] = expense_prediction
            delta = expense_prediction["predicted_change_from_latest"]
            direction = "increase" if delta > 0 else "decrease" if delta < 0 else "remain level"
            return {
                "answer": f"The validated next-month expense estimate indicates expenses may {direction} by {_money(abs(delta))} relative to the latest recorded expense month. This is a prediction from completed recorded months, not a recorded result or a guarantee.",
                "facts": facts,
            }
        if anomalies:
            first = anomalies[0]
            answer = f"The Phase 5 checks flagged {len(anomalies)} unusual spending item(s). {first['category']} is the largest listed flag: {_money(first['current_amount'])} versus a historical average of {_money(first['historical_average'])}. These are statistical flags, not fraud findings."
        elif increasing:
            changes = []
            for row in increasing[:3]:
                delta = row["current_amount"] - row["previous_amount"]
                changes.append(f"{row['category']} rose by {_money(delta)} ({row['change_percent']:.1f}%)")
            answer = f"Compared with the previous observed month, recorded spending increased in: {'; '.join(changes)}. These are comparisons from your category totals."
        elif summary["observed_months"] < 2:
            answer = "There isn't enough month-to-month history to explain an expense increase yet. Add records for another month and ask again."
        elif summary["observed_months"] < 4:
            answer = "There isn't enough monthly history to check category spending spikes reliably. The Phase 5 check needs at least three earlier observed months for comparison."
        else:
            answer = "The Phase 5 checks did not flag unusual spending for the selected period. These checks are statistical signals, not proof that every transaction is expected."
        return {"answer": answer, "facts": facts}

    if intent == Intent.RECOMMENDATION:
        recommendations = context.get("recommendations", [])
        facts["recommendations"] = recommendations
        if recommendations:
            answer = "Here are the highest-priority actions from the existing FlexiFund analysis: " + " ".join(
                f"{index}. {row['title']}: {row['message']}" for index, row in enumerate(recommendations[:3], 1)
            )
        else:
            answer = "The current records don't support a specific recommendation yet."
        return {"answer": answer, "facts": facts}

    if intent == Intent.GOAL:
        goal = context["goal_support"]
        facts.update({"goal_tracking_available": False, "emergency_fund_target": goal["emergency_fund_target"], "emergency_fund_minimum_target": goal["emergency_fund_minimum_target"]})
        answer = "FlexiFund does not store a personal savings goal yet, so I can't say whether you'll reach one. " + goal["message"]
        if goal["emergency_fund_target"] is not None:
            answer += f" The existing Phase 5 estimate suggests an emergency-fund target of {_money(goal['emergency_fund_minimum_target'])} to {_money(goal['emergency_fund_target'])}, based on observed essential expenses; this is not a saved personal goal."
        return {
            "answer": answer,
            "facts": facts,
        }

    facts.update({"recorded_income": summary["income"], "recorded_expenses": summary["expenses"], "recorded_surplus": summary["surplus"]})
    return {
        "answer": f"For {period}, your records show {_money(summary['income'])} income, {_money(summary['expenses'])} expenses, and {_money(summary['surplus'])} remaining. Ask about spending, savings, forecasts, financial health, or recommendations for a focused answer.",
        "facts": facts,
    }
