"""Flask route registration."""

from flask import Flask

from app.routes.auth_routes import auth_bp
from app.routes.assistant_routes import assistant_bp
from app.routes.demo import demo_bp
from app.routes.dashboard_routes import dashboard_bp
from app.routes.finance_routes import finance_bp
from app.routes.health import health_bp
from app.routes.intelligence_routes import intelligence_bp
from app.routes.personalization_routes import personalization_bp
from app.routes.transaction_import_routes import transaction_import_bp


def register_routes(app: Flask) -> None:
    """Register the API blueprints on the application."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(demo_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(intelligence_bp)
    app.register_blueprint(personalization_bp)
    app.register_blueprint(transaction_import_bp)
