"""Create the synthetic Ravi demo profile and its weekly history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import create_app
from app.database import create_tables, session_scope
from app.models import FinancialHistory, Rider

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


def main() -> None:
    app = create_app()
    create_tables(app)
    with app.app_context(), session_scope() as session:
        riders_created, history_created = seed_synthetic_rider(session)
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
    print(
        "Synthetic seed complete: "
        f"{1 if rider_count is not None else 0} Ravi rider, "
        f"{history_count or 0} history records; "
        f"added {riders_created} rider and {history_created} history records."
    )


if __name__ == "__main__":
    main()
