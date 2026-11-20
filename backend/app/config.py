"""Environment-backed application configuration."""

from __future__ import annotations

import os
from pathlib import Path

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
    DEBUG = _as_bool(os.getenv("DEBUG"))
    DATABASE_URL = os.getenv("DATABASE_URL")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
