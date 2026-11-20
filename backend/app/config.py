"""Environment-backed application configuration."""

from __future__ import annotations

import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Settings read from the environment and backend/.env."""

    APP_NAME = os.getenv("APP_NAME", "FlexiFund API")
    DEBUG = _as_bool(os.getenv("DEBUG", os.getenv("FLASK_DEBUG")))
    SECRET_KEY = os.getenv("SECRET_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///flexifund.db")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _as_bool(
        os.getenv("SESSION_COOKIE_SECURE"), default=not DEBUG
    )
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SESSION_REFRESH_EACH_REQUEST = False
    AI_PROVIDER = os.getenv("AI_PROVIDER", "disabled").strip().lower()
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "")
    AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "")
    AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "8"))
    # Kept outside the web root. Artifacts contain only fitted model parameters
    # and aggregate monthly expense values, never transaction descriptions.
    MODEL_STORE_DIR = os.getenv("MODEL_STORE_DIR", str(BACKEND_DIR / "model_store"))
