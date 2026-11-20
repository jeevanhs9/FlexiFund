"""Root and health endpoints for the FlexiFund API."""

from flask import Blueprint, current_app, jsonify

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
    return jsonify(
        {
            "status": "success",
            "message": "FlexiFund API is running",
        }
    )
