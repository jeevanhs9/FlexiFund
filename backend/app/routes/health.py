"""Root and health endpoints for the FlexiFund API."""

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import session_scope

health_bp = Blueprint("health", __name__)


@health_bp.get("/")
def root():
    return jsonify(
        {
            "message": "Welcome to FlexiFund API",
            "phase": "Phase 1 - Foundation",
        }
    )


@health_bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": current_app.config["APP_NAME"],
        }
    )


@health_bp.get("/api/health")
def api_health():
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return jsonify(
            {
                "status": "error",
                "message": "FlexiFund API is running but the database is unavailable.",
                "database": "unavailable",
            }
        ), 503
    return jsonify(
        {
            "status": "success",
            "message": "FlexiFund API and database are available.",
            "database": "available",
        }
    )
