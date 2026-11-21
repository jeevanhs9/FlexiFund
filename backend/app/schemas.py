"""Pydantic request and response validation for the REST API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

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
GoalCategory = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]


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


class RegisterCreate(BaseModel):
    name: NameText
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("A valid email address is required")
        return normalized


class LoginCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AssistantChatCreate(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    conversation_id: str | None = Field(default=None, min_length=36, max_length=36)
    user_id: int | None = Field(default=None, gt=0)


class FinancialGoalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NameText
    target_amount: PositiveMoney
    current_amount: NonNegativeMoney = Decimal("0.00")
    target_date: date
    priority: Literal["high", "medium", "low"] = "medium"
    category: GoalCategory | None = None
    user_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def current_amount_cannot_exceed_target(self):
        if self.current_amount > self.target_amount:
            raise ValueError("current_amount cannot exceed target_amount")
        return self

    @field_validator("target_date")
    @classmethod
    def target_date_must_be_future(cls, value: date) -> date:
        if value <= date.today():
            raise ValueError("target_date must be in the future")
        return value


class FinancialGoalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NameText | None = None
    target_amount: PositiveMoney | None = None
    current_amount: NonNegativeMoney | None = None
    target_date: date | None = None
    priority: Literal["high", "medium", "low"] | None = None
    category: GoalCategory | None = None
    status: Literal["active", "paused"] | None = None
    user_id: int | None = Field(default=None, gt=0)

    @field_validator("target_date")
    @classmethod
    def target_date_must_be_future(cls, value: date | None) -> date | None:
        if value is not None and value <= date.today():
            raise ValueError("target_date must be in the future")
        return value

    @model_validator(mode="after")
    def require_an_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        nullable_fields = {"name", "target_amount", "current_amount", "target_date", "priority", "status"}
        if any(field in self.model_fields_set and getattr(self, field) is None for field in nullable_fields):
            raise ValueError("Only category may be explicitly cleared")
        return self


ScenarioType = Literal[
    "reduce_expense_category",
    "increase_income",
    "decrease_recurring_expense",
    "add_recurring_expense",
    "increase_savings",
    "change_budget",
    "change_goal_contribution",
]


class ScenarioChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    change_type: ScenarioType
    amount: PositiveMoney
    category: ExpenseCategory | None = None
    goal_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_scenario_target(self):
        if self.change_type in {"reduce_expense_category", "change_budget", "add_recurring_expense", "decrease_recurring_expense"} and not self.category:
            raise ValueError("category is required for this scenario")
        if self.change_type == "change_goal_contribution" and self.goal_id is None:
            raise ValueError("goal_id is required for a goal-contribution scenario")
        return self


class ScenarioPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changes: Annotated[list[ScenarioChange], Field(min_length=1, max_length=8)]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] | None = None
    user_id: int | None = Field(default=None, gt=0)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class IncomeCreate(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
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
    user_id: int | None = Field(default=None, gt=0)
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


class ImportedTransactionUpdate(BaseModel):
    """A user correction for an imported bank transaction classification."""

    model_config = ConfigDict(extra="forbid")

    transaction_type: Literal["Income", "Expense", "Transfer", "Unknown"] | None = None
    category: ExpenseCategory | None = None
    is_work_expense: bool | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one classification field must be supplied")
        if self.transaction_type != "Expense" and "category" in self.model_fields_set and self.category is not None:
            # A category may be supplied together with transaction_type Expense.
            if "transaction_type" not in self.model_fields_set:
                return self
        return self
