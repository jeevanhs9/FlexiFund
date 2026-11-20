"""SQLAlchemy models for riders and their financial history."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Rider(Base):
    """A worker profile, marked synthetic when it is demo data."""

    __tablename__ = "riders"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "city",
            "persona_type",
            "is_synthetic",
            name="uq_riders_demo_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    persona_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(160), nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    financial_history: Mapped[list[FinancialHistory]] = relationship(
        back_populates="rider",
        cascade="all, delete-orphan",
        order_by="FinancialHistory.date",
    )


class FinancialHistory(Base):
    """A weekly record with work costs separate from household expenses."""

    __tablename__ = "financial_history"
    __table_args__ = (
        UniqueConstraint("rider_id", "date", name="uq_history_rider_date"),
        CheckConstraint("gross_income >= 0", name="ck_history_income_nonnegative"),
        CheckConstraint("fuel_cost >= 0", name="ck_history_fuel_nonnegative"),
        CheckConstraint(
            "maintenance_cost >= 0", name="ck_history_maintenance_nonnegative"
        ),
        CheckConstraint("data_cost >= 0", name="ck_history_data_nonnegative"),
        CheckConstraint(
            "other_work_cost >= 0", name="ck_history_other_work_nonnegative"
        ),
        CheckConstraint(
            "essential_expenses >= 0", name="ck_history_essentials_nonnegative"
        ),
        CheckConstraint("working_days BETWEEN 0 AND 7", name="ck_history_days_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rider_id: Mapped[int] = mapped_column(
        ForeignKey("riders.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    gross_income: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fuel_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    maintenance_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    data_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    other_work_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    essential_expenses: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    working_days: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    rider: Mapped[Rider] = relationship(back_populates="financial_history")
