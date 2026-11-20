"""Small deterministic intent router for common financial questions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re


class Intent(StrEnum):
    BALANCE = "BALANCE"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    SPENDING = "SPENDING"
    CATEGORY = "CATEGORY"
    BUDGET = "BUDGET"
    SAVINGS = "SAVINGS"
    FORECAST = "FORECAST"
    RISK = "RISK"
    GOAL = "GOAL"
    SCENARIO = "SCENARIO"
    ANOMALY = "ANOMALY"
    RECOMMENDATION = "RECOMMENDATION"
    FINANCIAL_HEALTH = "FINANCIAL_HEALTH"
    GENERAL = "GENERAL"


@dataclass(frozen=True)
class QueryAnalysis:
    intent: Intent
    category: str | None = None


_CATEGORY_TERMS = {
    "Food": ("food", "groceries", "grocery", "restaurant", "eating out"),
    "Rent": ("rent", "housing"),
    "Transportation": ("transport", "transportation", "travel", "commute", "fuel"),
    "Utilities": ("utilities", "utility", "electricity", "water bill"),
    "Education": ("education", "school", "tuition", "course"),
    "Healthcare": ("healthcare", "health care", "medical", "medicine"),
    "Entertainment": ("entertainment", "movies", "streaming"),
    "Shopping": ("shopping", "clothes", "clothing"),
    "EMI": ("emi", "loan payment", "installment"),
    "Insurance": ("insurance",),
    "Other": ("other expenses",),
}


def analyze_question(question: str) -> QueryAnalysis:
    """Classify an ordinary financial question without calling an LLM."""
    text = re.sub(r"\s+", " ", question.casefold()).strip()
    category = next(
        (
            name
            for name, phrases in _CATEGORY_TERMS.items()
            if any(re.search(rf"\b{re.escape(phrase)}\b", text) for phrase in phrases)
        ),
        None,
    )

    if re.search(r"\b(what if|what happens if|simulate|scenario)\b|\bif i (?:reduce|cut|lower|decrease|increase|add)\b", text):
        intent = Intent.SCENARIO
    elif re.search(r"\b(goal|target|prioriti[sz]e)\b", text):
        intent = Intent.GOAL
    elif re.search(r"\b(budget|budgeting|spending limit)\b", text):
        intent = Intent.BUDGET
    elif re.search(r"\b(forecast|predict|prediction|next month|will .* cost|will .* spend|are .* expenses? .* increas)\b", text):
        intent = Intent.FORECAST
    elif re.search(r"\b(risk|risky|financial risks?)\b", text):
        intent = Intent.RISK
    elif re.search(r"\b(recommend|recommendation|advice|suggest|should i|how can i|how do i reduce|ways to reduce|what should i reduce|hurting .* savings|most .* savings)\b", text):
        intent = Intent.RECOMMENDATION
    elif re.search(r"\b(anomal|unusual|spike|increased|increase|compared with|compared to|why .* expense)\b", text):
        intent = Intent.ANOMALY
    elif re.search(r"\b(where did i spend|top categories|highest spending)\b", text):
        intent = Intent.CATEGORY
    elif category and re.search(r"\b(spend|spent|spending|expense|expenses|category|where)\b", text):
        intent = Intent.CATEGORY
    elif re.search(r"\b(how am i doing|financial health|health score|healthy|overall finances?)\b", text):
        intent = Intent.FINANCIAL_HEALTH
    elif re.search(r"\b(balance|left over|leftover|surplus|cash flow)\b", text):
        intent = Intent.BALANCE
    elif re.search(r"\b(savings?|save|saved)\b", text):
        intent = Intent.SAVINGS
    elif re.search(r"\b(income|salary|earnings?|paycheck)\b", text):
        intent = Intent.INCOME
    elif re.search(r"\b(expenses?|costs?|spend|spent|spending)\b", text):
        intent = Intent.SPENDING if re.search(r"\b(spend|spent|spending)\b", text) else Intent.EXPENSE
    else:
        intent = Intent.GENERAL

    return QueryAnalysis(intent=intent, category=category if intent in {Intent.CATEGORY, Intent.ANOMALY, Intent.SCENARIO} else None)
