"""Simple, explainable financial health rules for Phase 2."""

from __future__ import annotations

from decimal import Decimal


def financial_status(savings_rate: Decimal, surplus: Decimal) -> str:
    """Classify a summary without treating a deficit as healthy."""
    if surplus < 0:
        return "Deficit"
    if savings_rate >= Decimal("20"):
        return "Healthy"
    if savings_rate >= Decimal("10"):
        return "Moderate"
    return "Needs Attention"


def health_indicators(summary: dict[str, Decimal]) -> dict[str, Decimal | str]:
    """Add deficit amount and rule-based status to calculator output."""
    surplus = summary["surplus"]
    return {
        "deficit": abs(surplus) if surplus < 0 else Decimal("0.00"),
        "financial_status": financial_status(summary["savings_rate"], surplus),
    }
