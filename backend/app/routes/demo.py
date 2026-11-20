"""Read-only endpoint for the synthetic rider dashboard."""

from flask import Blueprint, jsonify
from sqlalchemy import select

from app.database import session_scope
from app.models import FinancialHistory, Rider
from app.schemas import FinancialHistoryResponse, RiderResponse

demo_bp = Blueprint("demo", __name__, url_prefix="/api/demo")


@demo_bp.get("/rider")
def get_synthetic_rider():
    """Return Ravi's synthetic profile and weekly history without calculations."""
    with session_scope() as session:
        rider = session.scalar(
            select(Rider).where(
                Rider.name == "Ravi",
                Rider.city == "Bengaluru",
                Rider.persona_type == "delivery_rider",
                Rider.is_synthetic.is_(True),
            )
        )
        if rider is None:
            return jsonify({"error": "Synthetic rider data is not seeded yet."}), 404

        history = session.scalars(
            select(FinancialHistory)
            .where(FinancialHistory.rider_id == rider.id)
            .order_by(FinancialHistory.date)
        ).all()
        response = {
            "rider": RiderResponse.model_validate(rider).model_dump(mode="json"),
            "history": [
                FinancialHistoryResponse.model_validate(record).model_dump(mode="json")
                for record in history
            ],
        }

    return jsonify(response)
