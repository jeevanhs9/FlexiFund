"""Flask application factory for FlexiFund."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
import secrets
from typing import Any

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.config import Config
from app.database import init_database
from app.routes import register_routes


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    """Create and configure a FlexiFund Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    secret_key = app.config.get("SECRET_KEY")
    secret_text = str(secret_key or "")
    placeholder_key = any(
        marker in secret_text.casefold()
        for marker in ("replace", "change-me", "your-secret", "random_local")
    )
    if not secret_key or len(secret_text) < 32 or placeholder_key:
        if not app.config.get("DEBUG") and not app.config.get("TESTING"):
            raise RuntimeError("Set a random SECRET_KEY of at least 32 characters outside debug mode.")
        secret_key = secrets.token_urlsafe(48)
    app.config["SECRET_KEY"] = secret_key
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("PERMANENT_SESSION_LIFETIME", timedelta(hours=12))

    init_database(app)
    CORS(
        app,
        resources={r"/*": {"origins": app.config["FRONTEND_URL"]}},
        supports_credentials=True,
    )
    register_routes(app)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return jsonify({"status": "error", "message": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        # Exception messages can include SQL statements and bound financial values.
        app.logger.error("Unhandled API error (%s).", type(error).__name__)
        return jsonify(
            {"status": "error", "message": "An internal server error occurred."}
        ), 500

    return app
