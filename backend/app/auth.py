"""Cookie-session authentication and authorization helpers."""

from __future__ import annotations

import hmac
import secrets
from typing import Any

from flask import current_app, g, request, session
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import session_scope
from app.models import User
from app.routes.helpers import error_response, parse_json_body, success_response
from app.schemas import LoginCreate, RegisterCreate


def _origin_error():
    """Reject browser writes from origins outside the configured frontend."""
    origin = request.headers.get("Origin")
    allowed = str(current_app.config.get("FRONTEND_URL", "")).rstrip("/")
    if origin and origin.rstrip("/") != allowed:
        return error_response("Request origin is not allowed.", 403)
    return None


def _csrf_error():
    expected = session.get("csrf_token")
    provided = request.headers.get("X-CSRF-Token")
    if not isinstance(expected, str) or not isinstance(provided, str):
        return error_response("A valid CSRF token is required.", 403)
    if not hmac.compare_digest(expected, provided):
        return error_response("A valid CSRF token is required.", 403)
    return None


def authenticate_request():
    """Validate the signed session, load its account, and protect writes."""
    if request.method == "OPTIONS":
        return None
    if request.method not in {"GET", "HEAD"}:
        origin_error = _origin_error()
        if origin_error:
            return origin_error

    user_id = session.get("user_id")
    if not isinstance(user_id, int) or isinstance(user_id, bool):
        return error_response("Authentication is required.", 401)

    with session_scope() as database_session:
        user = database_session.get(User, user_id)
        if user is None or session.get("session_version") != user.session_version:
            session.clear()
            return error_response("Authentication is required.", 401)
        g.authenticated_user = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        }

    if request.method not in {"GET", "HEAD"}:
        csrf_error = _csrf_error()
        if csrf_error:
            return csrf_error
    return None


def authenticated_blueprint(blueprint):
    """Attach account authentication to every route in a private API blueprint."""
    blueprint.before_request(authenticate_request)
    return blueprint


def authenticated_user_id() -> int:
    return g.authenticated_user["id"]


def authorize_user_id(raw_user_id: str | None) -> tuple[int | None, Any | None]:
    """Allow omitted/current IDs and reject malformed or cross-account overrides."""
    current_user_id = authenticated_user_id()
    if raw_user_id is None:
        return current_user_id, None
    try:
        requested_user_id = int(raw_user_id)
    except (TypeError, ValueError):
        return None, error_response("user_id must be an integer.", 400)
    if requested_user_id < 1:
        return None, error_response("user_id must be a positive integer.", 400)
    if requested_user_id != current_user_id:
        return None, error_response("You are not authorized to access that account.", 403)
    return current_user_id, None


def authorize_body_user_id(requested_user_id: int | None):
    if requested_user_id is not None and requested_user_id != authenticated_user_id():
        return error_response("You are not authorized to access that account.", 403)
    return None


def _user_json(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "created_at": user.created_at.isoformat(),
    }


def _start_session(user: User) -> dict[str, Any]:
    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    session["session_version"] = user.session_version
    session["csrf_token"] = secrets.token_urlsafe(32)
    return {"user": _user_json(user), "csrf_token": session["csrf_token"]}


def register_account(payload: RegisterCreate):
    try:
        with session_scope() as database_session:
            existing = database_session.scalar(
                select(User).where(func.lower(User.email) == payload.email)
            )
            if existing is not None:
                return error_response("An account with this email already exists.", 409)
            user = User(
                name=payload.name,
                email=payload.email,
                password_hash=generate_password_hash(payload.password, method="scrypt"),
            )
            database_session.add(user)
            database_session.flush()
            user_id = user.id
    except IntegrityError:
        return error_response("An account with this email already exists.", 409)

    with session_scope() as database_session:
        user = database_session.get(User, user_id)
        session_data = _start_session(user)
    return success_response(session_data, 201)


def login_account(payload: LoginCreate):
    with session_scope() as database_session:
        user = database_session.scalar(
            select(User).where(func.lower(User.email) == payload.email)
        )
        if user is None or not user.password_hash or not check_password_hash(
            user.password_hash, payload.password
        ):
            return error_response("Email or password is incorrect.", 401)
        session_data = _start_session(user)
    return success_response(session_data)


def register_auth_routes(blueprint):
    """Install auth-only route protection and the standard session endpoints."""
    blueprint.before_request(_origin_error_for_unsafe_auth_routes)

    @blueprint.post("/register")
    def register():
        payload, error = parse_json_body(RegisterCreate)
        if error:
            return error_response(error)
        return register_account(payload)

    @blueprint.post("/login")
    def login():
        payload, error = parse_json_body(LoginCreate)
        if error:
            return error_response(error)
        return login_account(payload)

    @blueprint.get("/me")
    def current_user():
        auth_error = authenticate_request()
        if auth_error:
            return auth_error
        if not session.get("csrf_token"):
            session["csrf_token"] = secrets.token_urlsafe(32)
        session.permanent = True
        return success_response(
            {
                "user": g.authenticated_user,
                "csrf_token": session["csrf_token"],
            }
        )

    @blueprint.post("/logout")
    def logout():
        auth_error = authenticate_request()
        if auth_error:
            return auth_error
        with session_scope() as database_session:
            user = database_session.get(User, authenticated_user_id())
            if user is not None:
                user.session_version += 1
        session.clear()
        return success_response({"message": "You have been signed out."})


def _origin_error_for_unsafe_auth_routes():
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None
    origin_error = _origin_error()
    if origin_error:
        return origin_error
    if request.endpoint in {"auth.register", "auth.login"}:
        return None
    return authenticate_request()
