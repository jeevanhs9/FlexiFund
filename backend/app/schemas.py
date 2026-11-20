"""Pydantic request and response validation for the REST API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

NonNegativeMoney = Annotated[
    Decimal,
    Field(ge=Decimal("0"), max_digits=12, decimal_places=2),
]
PositiveMoney = Annotated[
    Decimal,
    Field(gt=Decimal("0"), max_digits=12, decimal_places=2),
]
IncomeType = Literal["Salary", "Freelance", "Business", "Investment", "Other"]
ExpenseCategory = Literal[
    "Food",
    "Rent",
    "Transportation",
    "Utilities",
    "Education",
    "Healthcare",
    "Entertainment",
    "Shopping",
    "EMI",
    "Insurance",
    "Other",
]
ExpenseType = Literal["Essential", "Non-Essential"]
NameText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


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


class UserCreate(BaseModel):
    name: NameText
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("A valid email address is required")
        return normalized


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class IncomeCreate(BaseModel):
    user_id: int = Field(gt=0)
    source: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    amount: PositiveMoney
    income_type: IncomeType
    date: date
    description: str | None = Field(default=None, max_length=500)


class IncomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    source: str
    amount: Decimal
    income_type: str
    date: date
    description: str | None
    created_at: datetime


class ExpenseCreate(BaseModel):
    user_id: int = Field(gt=0)
    category: ExpenseCategory
    amount: PositiveMoney
    expense_type: ExpenseType
    date: date
    description: str | None = Field(default=None, max_length=500)


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category: str
    amount: Decimal
    expense_type: str
    date: date
    description: str | None
    created_at: datetime
