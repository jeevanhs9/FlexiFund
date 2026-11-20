"""Flask route registration."""

from flask import Flask

from app.routes.demo import demo_bp
from app.routes.dashboard_routes import dashboard_bp
from app.routes.finance_routes import finance_bp
from app.routes.health import health_bp


def register_routes(app: Flask) -> None:
    """Register the API blueprints on the application."""
    app.register_blueprint(health_bp)
    app.register_blueprint(demo_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(dashboard_bp)
