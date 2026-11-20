"""Flask application factory for FlexiFund."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.database import init_database
from app.routes import register_routes


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    """Create and configure a FlexiFund Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    init_database(app)
    CORS(
        app,
        resources={r"/*": {"origins": app.config["FRONTEND_URL"]}},
    )
    register_routes(app)
    return app
