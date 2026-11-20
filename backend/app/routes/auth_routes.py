"""Authentication endpoints for registration, login, and cookie sessions."""

from flask import Blueprint

from app.auth import register_auth_routes

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
register_auth_routes(auth_bp)
