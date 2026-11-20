"""Pydantic request and response validation for the REST API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NonNegativeMoney = Annotated[
    Decimal,
    Field(ge=Decimal("0"), max_digits=12, decimal_places=2),
]


class RiderBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=1, max_length=120)
    persona_type: str = Field(min_length=1, max_length=60)
    platform: str = Field(min_length=1, max_length=160)
    is_synthetic: bool = False


class RiderCreate(RiderBase):
    pass


class RiderResponse(RiderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class FinancialHistoryBase(BaseModel):
    date: date
    gross_income: NonNegativeMoney
    fuel_cost: NonNegativeMoney
    maintenance_cost: NonNegativeMoney
    data_cost: NonNegativeMoney
    other_work_cost: NonNegativeMoney
    essential_expenses: NonNegativeMoney
    working_days: int = Field(ge=0, le=7)
    notes: str | None = None


class FinancialHistoryCreate(FinancialHistoryBase):
    rider_id: int = Field(gt=0)


class FinancialHistoryResponse(FinancialHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rider_id: int
    created_at: datetime
