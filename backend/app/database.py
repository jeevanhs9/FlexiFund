"""SQLAlchemy engine and session lifecycle helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from flask import Flask, current_app, has_app_context
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


def init_database(app: Flask) -> None:
    """Create an engine and session factory for this Flask app."""
    database_url = app.config.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy backend/.env.example to backend/.env."
        )
    is_sqlite = database_url.startswith("sqlite:")
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )
    if is_sqlite:
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    app.extensions["flexifund_engine"] = engine
    app.extensions["flexifund_session_factory"] = session_factory


def get_engine(app: Flask | None = None) -> Engine:
    """Return the engine associated with an app or the active app context."""
    target_app = app or _get_current_app()
    return target_app.extensions["flexifund_engine"]


@contextmanager
def session_scope(app: Flask | None = None) -> Iterator[Session]:
    """Open a transaction, commit on success, and roll back on errors."""
    target_app = app or _get_current_app()
    session_factory = target_app.extensions["flexifund_session_factory"]
    with session_factory.begin() as session:
        yield session


def create_tables(app: Flask | None = None) -> None:
    """Create all mapped tables if they do not already exist."""
    from app import models  # noqa: F401  Register model metadata before create_all.

    Base.metadata.create_all(bind=get_engine(app))


def _get_current_app() -> Flask:
    if not has_app_context():
        raise RuntimeError("Pass a Flask app or enter its application context first.")
    return current_app._get_current_object()


def _enable_sqlite_foreign_keys(connection, _connection_record) -> None:
    """Enable SQLite foreign-key enforcement on every pooled connection."""
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
