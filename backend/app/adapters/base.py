"""Shared interface for normalizing persona-specific financial records."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import TypedDict

from app.models import FinancialHistory


class NormalizedFinancialRecord(TypedDict):
    """Canonical, calculation-free representation of a history record."""

    date: date
    gross_income: Decimal
    fuel_cost: Decimal
    maintenance_cost: Decimal
    data_cost: Decimal
    other_work_cost: Decimal
    essential_expenses: Decimal
    working_days: int
    notes: str | None


class PersonaAdapter(ABC):
    """Interface for mapping a persona's history into the common data shape."""

    @property
    @abstractmethod
    def persona_type(self) -> str:
        """Return the canonical persona identifier supported by this adapter."""

    @abstractmethod
    def normalize_history_record(
        self, record: FinancialHistory
    ) -> NormalizedFinancialRecord:
        """Return canonical fields without calculating financial outcomes."""
