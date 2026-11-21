"""SQLAlchemy models for riders and their financial history."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
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


class User(Base):
    """A FlexiFund account used to group income and expense records."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    incomes: Mapped[list[Income]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Income.date",
    )
    expenses: Mapped[list[Expense]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Expense.date",
    )
    import_batches: Mapped[list[ImportBatch]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="ImportBatch.created_at.desc()",
    )
    imported_transactions: Mapped[list[ImportedTransaction]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="ImportedTransaction.transaction_date.desc(), ImportedTransaction.id.desc()",
    )
    classification_preferences: Mapped[list[TransactionClassificationPreference]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Income(Base):
    """A dated income entry. Amounts use decimal-compatible storage."""

    __tablename__ = "income"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_income_amount_positive"),
        Index("ix_income_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    income_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[User] = relationship(back_populates="incomes")


class Expense(Base):
    """A dated expense entry with an essentiality classification."""

    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        Index("ix_expenses_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expense_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[User] = relationship(back_populates="expenses")


class AssistantMessage(Base):
    """A user-owned assistant conversation message."""

    __tablename__ = "assistant_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_assistant_message_role"),
        Index("ix_assistant_messages_user_conversation", "user_id", "conversation_id", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(12), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class FinancialGoal(Base):
    """A user-owned savings target and its current progress."""

    __tablename__ = "financial_goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_goal_target_positive"),
        CheckConstraint("current_amount >= 0", name="ck_goal_current_nonnegative"),
        CheckConstraint("priority IN ('high', 'medium', 'low')", name="ck_goal_priority"),
        CheckConstraint("status IN ('active', 'paused', 'completed')", name="ck_goal_status"),
        Index("ix_financial_goals_user_status_target", "user_id", "status", "target_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(12), nullable=False, default="medium")
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    contributions: Mapped[list[GoalContribution]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", order_by="GoalContribution.contributed_at"
    )


class GoalContribution(Base):
    """A user-recorded goal balance adjustment, with its direction preserved."""

    __tablename__ = "goal_contributions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_goal_contribution_positive"),
        CheckConstraint("change_type IN ('opening_balance', 'contribution', 'withdrawal')", name="ck_goal_contribution_type"),
        Index("ix_goal_contributions_user_goal_date", "user_id", "goal_id", "contributed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(
        ForeignKey("financial_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    change_type: Mapped[str] = mapped_column(String(12), nullable=False, default="contribution")
    contributed_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    goal: Mapped[FinancialGoal] = relationship(back_populates="contributions")


class ImportBatch(Base):
    """A user-owned, metadata-only record of one CSV import attempt."""

    __tablename__ = "import_batches"
    __table_args__ = (
        UniqueConstraint("batch_code", name="uq_import_batches_code"),
        Index("ix_import_batches_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_code: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="csv")
    mapping_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped[User] = relationship(back_populates="import_batches")
    transactions: Mapped[list[ImportedTransaction]] = relationship(
        back_populates="import_batch", cascade="all, delete-orphan", order_by="ImportedTransaction.id"
    )


class ImportedTransaction(Base):
    """Normalized bank-statement row with traceable classification metadata.

    Financial analysis continues to use the existing Income and Expense models.
    The optional linked IDs show exactly which canonical record was created from
    this imported row without storing the original CSV content.
    """

    __tablename__ = "imported_transactions"
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('Income', 'Expense', 'Transfer', 'Unknown')",
            name="ck_imported_transaction_type",
        ),
        CheckConstraint(
            "review_status IN ('classified', 'needs_review', 'corrected')",
            name="ck_imported_transaction_review_status",
        ),
        CheckConstraint(
            "amount > 0", name="ck_imported_transaction_amount_positive"
        ),
        Index("ix_imported_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_imported_transactions_user_reference", "user_id", "reference_id"),
        Index("ix_imported_transactions_user_fingerprint", "user_id", "duplicate_fingerprint"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    import_batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    debit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    credit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    payment_mode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_work_expense: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_recurring: Mapped[bool] = mapped_column(nullable=False, default=False)
    classification_confidence: Mapped[str] = mapped_column(String(12), nullable=False, default="low")
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="needs_review")
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="csv")
    duplicate_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    linked_income_id: Mapped[int | None] = mapped_column(
        ForeignKey("income.id", ondelete="SET NULL"), nullable=True, index=True
    )
    linked_expense_id: Mapped[int | None] = mapped_column(
        ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[User] = relationship(back_populates="imported_transactions")
    import_batch: Mapped[ImportBatch] = relationship(back_populates="transactions")


class TransactionClassificationPreference(Base):
    """A per-user merchant correction reused by future CSV imports."""

    __tablename__ = "transaction_classification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "merchant_key", name="uq_transaction_preference_user_merchant"),
        Index("ix_transaction_preferences_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    merchant_key: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(16), nullable=False)
    is_work_expense: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[User] = relationship(back_populates="classification_preferences")
