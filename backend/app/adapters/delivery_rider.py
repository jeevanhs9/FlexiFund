"""Normalization adapter for delivery-rider financial history."""

from __future__ import annotations

from app.adapters.base import NormalizedFinancialRecord, PersonaAdapter
from app.models import FinancialHistory


class DeliveryRiderAdapter(PersonaAdapter):
    """Expose delivery rider records through FlexiFund's canonical fields."""

    @property
    def persona_type(self) -> str:
        return "delivery_rider"

    def normalize_history_record(
        self, record: FinancialHistory
    ) -> NormalizedFinancialRecord:
        return {
            "date": record.date,
            "gross_income": record.gross_income,
            "fuel_cost": record.fuel_cost,
            "maintenance_cost": record.maintenance_cost,
            "data_cost": record.data_cost,
            "other_work_cost": record.other_work_cost,
            "essential_expenses": record.essential_expenses,
            "working_days": record.working_days,
            "notes": record.notes,
        }
