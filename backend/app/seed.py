"""Create the synthetic Ravi demo profile and its weekly history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import create_app
from app.constants import (
    DEMO_TRANSACTION_DATE,
    DEMO_USER_EMAIL,
    DEMO_USER_NAME,
    DEMO_USER_PASSWORD,
)
from app.database import create_tables, session_scope
from app.models import Expense, FinancialHistory, Income, Rider, User
from werkzeug.security import generate_password_hash

SYNTHETIC_HISTORY_END_DATE = date(2026, 11, 16)


@dataclass(frozen=True)
class WeeklyPattern:
    gross_income: int
    working_days: int
    fuel_cost: int
    maintenance_cost: int
    data_cost: int
    other_work_cost: int
    essential_expenses: int
    notes: str


# Eight months of deliberately authored patterns. Values are rupees per week.
WEEKLY_PATTERNS: tuple[WeeklyPattern, ...] = (
    WeeklyPattern(6500, 6, 1150, 120, 100, 180, 3900, "Normal earning week."),
    WeeklyPattern(6100, 5, 980, 100, 100, 160, 3900, "Normal week with one fewer workday."),
    WeeklyPattern(7000, 6, 1240, 120, 110, 190, 4050, "Normal earning week."),
    WeeklyPattern(6700, 6, 1180, 100, 100, 170, 4050, "Normal earning week."),
    WeeklyPattern(4700, 4, 790, 100, 90, 130, 4050, "Rain-affected week; fewer shifts and lower demand."),
    WeeklyPattern(4200, 4, 760, 100, 90, 120, 4050, "Heavy rain reduced working days and earnings."),
    WeeklyPattern(7300, 6, 1260, 120, 110, 190, 4100, "Recovery to a normal six-day week."),
    WeeklyPattern(7600, 6, 1310, 120, 110, 190, 4100, "Strong demand period begins."),
    WeeklyPattern(8200, 6, 1390, 120, 110, 210, 4100, "Strong earning week with extra shifts."),
    WeeklyPattern(7900, 6, 1360, 120, 110, 200, 4100, "Strong demand period."),
    WeeklyPattern(7500, 6, 1300, 120, 110, 190, 4150, "Strong period returns to normal."),
    WeeklyPattern(6800, 6, 1190, 100, 100, 170, 4150, "Normal earning week."),
    WeeklyPattern(6400, 5, 1010, 100, 100, 160, 4150, "Normal week with five working days."),
    WeeklyPattern(7100, 6, 1230, 120, 110, 180, 4200, "Normal earning week."),
    WeeklyPattern(6600, 5, 1080, 100, 100, 160, 4200, "Normal week with one fewer workday."),
    WeeklyPattern(5000, 5, 930, 100, 90, 140, 4200, "Lean period begins; fewer delivery orders."),
    WeeklyPattern(4500, 4, 780, 100, 90, 130, 4200, "Lean month; low order volume."),
    WeeklyPattern(4800, 5, 910, 100, 90, 130, 4200, "Lean month continues."),
    WeeklyPattern(
        4300,
        4,
        770,
        1450,
        90,
        120,
        4200,
        "Final weak week of the lean period; rear tyre and brake maintenance event.",
    ),
    WeeklyPattern(6200, 5, 1030, 100, 100, 160, 4250, "Gradual recovery after the lean period."),
    WeeklyPattern(7000, 6, 1200, 120, 110, 180, 4250, "Normal earning week."),
    WeeklyPattern(7400, 6, 1270, 120, 110, 190, 4250, "Normal earning week."),
    WeeklyPattern(6800, 5, 1100, 100, 100, 170, 4300, "Normal week with five working days."),
    WeeklyPattern(9800, 6, 1530, 150, 110, 240, 4300, "Festival demand spike; synthetic high-income week."),
    WeeklyPattern(8700, 6, 1460, 120, 110, 220, 4300, "Festival demand remains elevated."),
    WeeklyPattern(6500, 5, 1050, 100, 100, 160, 4350, "Post-festival return to normal demand."),
    WeeklyPattern(6100, 5, 1010, 100, 100, 150, 4350, "Normal earning week."),
    WeeklyPattern(3900, 4, 740, 100, 90, 120, 4350, "Rain-affected week with fewer shifts."),
    WeeklyPattern(5600, 5, 990, 100, 100, 150, 4400, "Weak demand and a shorter working week."),
    WeeklyPattern(6900, 6, 1210, 100, 110, 180, 4400, "Normal earning week."),
    WeeklyPattern(7200, 6, 1250, 120, 110, 180, 4400, "Normal earning week."),
    WeeklyPattern(6400, 5, 1050, 100, 100, 160, 4450, "Normal week with five working days."),
)

SAMPLE_EXPENSES: tuple[tuple[str, int, str, str], ...] = (
    ("Rent", 12000, "Essential", "Monthly rent"),
    ("Food", 5000, "Essential", "Monthly food expenses"),
    ("Transportation", 3000, "Essential", "Local transportation"),
    ("Utilities", 2000, "Essential", "Monthly utility bills"),
    ("Entertainment", 2000, "Non-Essential", "Entertainment budget"),
    ("Shopping", 3000, "Non-Essential", "Monthly shopping"),
    ("Education", 3000, "Essential", "Education expenses"),
)

# The finance presentation account is intentionally synthetic. Twelve completed
# months unlock the ML expense model; the current month keeps dashboard cards
# populated. Values are varied to make trend, risk, budget and forecast views
# useful during a demo while staying separate from private accounts.
FINANCE_DEMO_MONTHS: tuple[tuple[int, tuple[int, int, int, int, int, int, int]], ...] = (
    (48200, (11700, 5100, 2800, 1900, 1200, 1900, 2500)),
    (49600, (11900, 5300, 2900, 2000, 1300, 2100, 2500)),
    (48800, (11900, 5000, 2700, 1900, 1100, 1800, 2500)),
    (50500, (12000, 5400, 3000, 2100, 1400, 2400, 2600)),
    (51200, (12000, 5600, 3050, 2100, 1500, 2600, 2600)),
    (50100, (12100, 5500, 3000, 2050, 1400, 2200, 2600)),
    (51800, (12100, 5800, 3100, 2150, 1550, 2800, 2700)),
    (52600, (12200, 6000, 3200, 2200, 1600, 3000, 2700)),
    (51400, (12200, 5700, 3050, 2150, 1450, 2500, 2700)),
    (53500, (12300, 6200, 3300, 2250, 1700, 3300, 2800)),
    (54800, (12300, 6500, 3350, 2300, 1800, 3600, 2800)),
    (54000, (12400, 6300, 3250, 2250, 1650, 3100, 2800)),
)


def _shift_month(base: date, offset: int) -> date:
    value = base.year * 12 + base.month - 1 + offset
    return date(value // 12, value % 12 + 1, 1)


def _money(amount: int) -> Decimal:
    return Decimal(amount).quantize(Decimal("0.01"))


def _week_start_dates(count: int) -> list[date]:
    current_monday = SYNTHETIC_HISTORY_END_DATE
    first_monday = current_monday - timedelta(weeks=count - 1)
    return [first_monday + timedelta(weeks=offset) for offset in range(count)]


def seed_synthetic_rider(session: Session) -> tuple[int, int]:
    """Insert Ravi and any missing demo history rows, returning added counts."""
    rider = session.scalar(
        select(Rider).where(
            Rider.name == "Ravi",
            Rider.city == "Bengaluru",
            Rider.persona_type == "delivery_rider",
            Rider.is_synthetic.is_(True),
        )
    )
    riders_created = 0
    if rider is None:
        rider = Rider(
            name="Ravi",
            city="Bengaluru",
            persona_type="delivery_rider",
            platform="Synthetic Delivery Platform",
            is_synthetic=True,
        )
        session.add(rider)
        session.flush()
        riders_created = 1

    existing_dates = set(
        session.scalars(
            select(FinancialHistory.date).where(FinancialHistory.rider_id == rider.id)
        ).all()
    )
    history_created = 0
    for week_start, pattern in zip(
        _week_start_dates(len(WEEKLY_PATTERNS)), WEEKLY_PATTERNS
    ):
        if week_start in existing_dates:
            continue
        session.add(
            FinancialHistory(
                rider_id=rider.id,
                date=week_start,
                gross_income=_money(pattern.gross_income),
                fuel_cost=_money(pattern.fuel_cost),
                maintenance_cost=_money(pattern.maintenance_cost),
                data_cost=_money(pattern.data_cost),
                other_work_cost=_money(pattern.other_work_cost),
                essential_expenses=_money(pattern.essential_expenses),
                working_days=pattern.working_days,
                notes=pattern.notes,
            )
        )
        history_created += 1
    return riders_created, history_created


def seed_financial_demo(session: Session) -> tuple[int, int, int]:
    """Create an idempotent, sign-inable synthetic presentation account."""
    user = session.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    users_created = 0
    if user is None:
        user = User(
            name=DEMO_USER_NAME,
            email=DEMO_USER_EMAIL,
            password_hash=generate_password_hash(DEMO_USER_PASSWORD, method="scrypt"),
        )
        session.add(user)
        session.flush()
        users_created = 1
    elif not user.password_hash:
        # A legacy seeded account was never intended to hold private data, so
        # adding the documented demo password makes it presentable without
        # altering any real user's credentials.
        user.password_hash = generate_password_hash(DEMO_USER_PASSWORD, method="scrypt")

    income_created = 0
    expenses_created = 0
    expense_template = tuple((category, expense_type, description) for category, _amount, expense_type, description in SAMPLE_EXPENSES)
    # Completed history covers the preceding 12 months. Current records make
    # the live dashboard informative as soon as the seed is run.
    for offset, (income_amount, expense_amounts) in zip(range(-12, 0), FINANCE_DEMO_MONTHS):
        transaction_date = _shift_month(DEMO_TRANSACTION_DATE, offset)
        matching_income = session.scalar(
            select(Income.id).where(
                Income.user_id == user.id,
                Income.source == "Demo consulting income",
                Income.amount == _money(income_amount),
                Income.date == transaction_date,
            )
        )
        if matching_income is None:
            session.add(Income(
                user_id=user.id, source="Demo consulting income", amount=_money(income_amount),
                income_type="Freelance", date=transaction_date,
                description="Synthetic presentation income",
            ))
            income_created += 1
        for (category, expense_type, description), amount in zip(expense_template, expense_amounts):
            matching_expense = session.scalar(
                select(Expense.id).where(
                    Expense.user_id == user.id, Expense.category == category,
                    Expense.amount == _money(amount), Expense.expense_type == expense_type,
                    Expense.date == transaction_date,
                )
            )
            if matching_expense is None:
                session.add(Expense(
                    user_id=user.id, category=category, amount=_money(amount),
                    expense_type=expense_type, date=transaction_date,
                    description=f"{description} — synthetic presentation data",
                ))
                expenses_created += 1

    # Keep the original current-month sample amounts for a simple ₹50k / ₹30k
    # headline while marking every row as synthetic.
    matching_income = session.scalar(select(Income.id).where(
        Income.user_id == user.id, Income.source == "Salary", Income.income_type == "Salary",
        Income.amount == _money(50000), Income.date == DEMO_TRANSACTION_DATE,
    ))
    if matching_income is None:
        session.add(Income(user_id=user.id, source="Salary", amount=_money(50000), income_type="Salary", date=DEMO_TRANSACTION_DATE, description="Monthly salary — synthetic presentation data"))
        income_created += 1
    for category, amount, expense_type, description in SAMPLE_EXPENSES:
        matching_expense = session.scalar(select(Expense.id).where(
            Expense.user_id == user.id, Expense.category == category, Expense.amount == _money(amount),
            Expense.expense_type == expense_type, Expense.date == DEMO_TRANSACTION_DATE,
        ))
        if matching_expense is None:
            session.add(Expense(user_id=user.id, category=category, amount=_money(amount), expense_type=expense_type, date=DEMO_TRANSACTION_DATE, description=f"{description} — synthetic presentation data"))
            expenses_created += 1
    return users_created, income_created, expenses_created


def main() -> None:
    app = create_app()
    create_tables(app)
    with app.app_context(), session_scope() as session:
        riders_created, history_created = seed_synthetic_rider(session)
        users_created, incomes_created, expenses_created = seed_financial_demo(session)
        session.flush()
        rider_count = session.scalar(
            select(func.count(Rider.id)).where(
                Rider.name == "Ravi",
                Rider.city == "Bengaluru",
                Rider.persona_type == "delivery_rider",
                Rider.is_synthetic.is_(True),
            )
        )
        history_count = session.scalar(
            select(func.count(FinancialHistory.id)).join(Rider).where(
                Rider.name == "Ravi",
                Rider.city == "Bengaluru",
                Rider.persona_type == "delivery_rider",
                Rider.is_synthetic.is_(True),
            )
        )
        finance_user = session.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
        finance_income_count = session.scalar(
            select(func.count(Income.id)).where(Income.user_id == finance_user.id)
        )
        finance_expense_count = session.scalar(
            select(func.count(Expense.id)).where(Expense.user_id == finance_user.id)
        )
    print(
        "Synthetic seed complete: "
        f"{1 if rider_count is not None else 0} Ravi rider, "
        f"{history_count or 0} rider history records; "
        f"{1 if finance_user is not None else 0} finance demo user, "
        f"{finance_income_count or 0} income records and "
        f"{finance_expense_count or 0} expense records; "
        f"added {riders_created} rider, {history_created} rider history, "
        f"{users_created} finance user, {incomes_created} income, "
        f"and {expenses_created} expenses."
    )


if __name__ == "__main__":
    main()
