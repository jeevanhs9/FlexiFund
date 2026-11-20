"""Prioritized recommendations generated from measured analysis outputs."""

from __future__ import annotations

from decimal import Decimal


def generate_recommendations(summary: dict, spending: dict, forecast: dict, risk: dict, quality: dict, anomalies: list | None = None) -> list[dict]:
    recommendations = []
    if quality["valid_rows"] == 0:
        return [{"priority": "INFO", "title": "Add financial transactions", "message": "Add income and expense records to unlock spending analysis, risk scoring and forecasts.", "basis": "No valid transactions are available for this account."}]
    if summary["total_income"] == 0 and summary["total_expenses"] == 0:
        return [{"priority": "INFO", "title": "No records in this period", "message": "There are no transactions for the selected period. Choose another period or add records for this month.", "basis": "Transactions exist outside the selected period."}]

    if summary["surplus"] < 0:
        recommendations.append({"priority": "CRITICAL", "title": "Address the recorded cash-flow deficit", "message": f"Recorded expenses exceed income by ₹{abs(summary['surplus']):,.2f} for this period. Review recurring costs and upcoming bills.", "basis": "Selected-period income minus selected-period expenses."})
    elif summary["total_income"] > 0 and summary["savings_rate"] < Decimal("10"):
        recommendations.append({"priority": "HIGH", "title": "Build a larger monthly buffer", "message": f"Your recorded savings rate is {summary['savings_rate']:.1f}%. Review discretionary expenses and set a realistic amount to retain.", "basis": "Selected-period savings rate."})

    for item in spending["overspending"]:
        recommendations.append({"priority": "HIGH" if item["severity"] == "high" else "MEDIUM", "title": f"Review {item['category']} spending", "message": f"{item['category']} is ₹{item['current_amount'] - item['historical_average']:,.2f} above its recent average ({item['increase_percentage']:.1f}% higher). Check whether the increase is expected.", "basis": f"Compared with {item['baseline_months']} prior observed category totals using mean + 1.5 standard deviations and a 25% floor."})

    for anomaly in anomalies or []:
        if not any(item.get("title") == f"Review {anomaly['category']} spending" for item in recommendations):
            recommendations.append({"priority": "MEDIUM", "title": f"Check unusual {anomaly['category']} spending", "message": f"Recorded {anomaly['category']} spending of ₹{anomaly['current_amount']:,.2f} exceeded its historical comparison threshold.", "basis": anomaly["explanation"]})

    if risk.get("risk_factors"):
        for factor in risk["risk_factors"]:
            if factor["factor"] == "Declining Savings":
                recommendations.append({"priority": "HIGH", "title": "Review the downward savings trend", "message": "Savings have fallen across the last three observed monthly records. Compare planned and actual spending before setting a new savings target.", "basis": factor["message"]})
    if forecast["available"] and forecast["predicted_savings"] < 0:
        recommendations.append({"priority": "HIGH", "title": "Plan for a possible negative cash flow", "message": f"The statistical estimate for {forecast['forecast_month']} is a shortfall of ₹{abs(forecast['predicted_savings']):,.2f}. Review expected income and essential costs.", "basis": forecast["explanation"]})
    expense_prediction = forecast.get("expense_prediction")
    if expense_prediction and expense_prediction.get("available") and expense_prediction["predicted_change_from_latest"] > 0:
        recommendations.append({
            "priority": "MEDIUM",
            "title": "Plan for a possible expense increase",
            "message": f"The validated model estimates next-month expenses at ₹{expense_prediction['predicted_expenses']:,.2f}, about ₹{expense_prediction['predicted_change_from_latest']:,.2f} above the latest recorded expense month.",
            "basis": "This is a model prediction based on completed recorded expense months and chronological validation; it is not a recorded expense or a guarantee.",
        })
    discretionary = summary["non_essential_expenses"]
    if discretionary > 0:
        possible_saving = (discretionary * Decimal("0.10")).quantize(Decimal("0.01"))
        recommendations.append({"priority": "LOW", "title": "Consider a discretionary spending target", "message": f"A hypothetical 10% reduction in selected-period non-essential expenses would retain about ₹{possible_saving:,.2f}; this is an illustration, not a guaranteed saving.", "basis": "10% of recorded non-essential expenses for the selected period."})
    if quality["warnings"]:
        recommendations.append({"priority": "MEDIUM", "title": "Review transaction data quality", "message": quality["warnings"][0], "basis": "The preprocessing stage validates rows and retains duplicate candidates without deleting them."})
    if not forecast["available"]:
        recommendations.append({"priority": "INFO", "title": "Build more monthly history", "message": forecast["explanation"], "basis": "Forecast fallback rule."})
    return recommendations
