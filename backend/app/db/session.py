"""
SQLAlchemy session setup with FastAPI-compatible dependency.

- ENGINE: Synchronous engine (SQLite by default).
- SessionLocal: sessionmaker factory bound to the engine.
- get_db(): Yields a session per request and ensures it is closed.

Database URL resolution (priority):
1) Env var DATABASE_URL or DB_URL
2) app.core.config.get_settings().db_url
3) Fallback to sqlite:///./app.db
"""

from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

__all__ = ["engine", "SessionLocal", "get_db", "DATABASE_URL", "SQLALCHEMY_ECHO"]

# -------------------------------
# Configuration
# -------------------------------

# Prefer explicit env overrides first
_env_db_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
if _env_db_url:
    DATABASE_URL: str = _env_db_url
else:
    # Fall back to application settings if available
    try:
        from app.core.config import get_settings  # local import to avoid cycles

        DATABASE_URL = get_settings().db_url
    except Exception:
        # Safe final fallback
        DATABASE_URL = "sqlite:///./app.db"

SQLALCHEMY_ECHO: bool = os.getenv("SQLALCHEMY_ECHO", "0").lower() in {"1", "true", "yes", "on"}

# -------------------------------
# Engine
# -------------------------------

# SQLite needs check_same_thread=False for multithreaded apps (e.g., FastAPI with Uvicorn)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=SQLALCHEMY_ECHO,
    )

    # Ensure FK constraints are enforced on every connection (SQLite default is OFF)
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # pragma: no cover
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()
else:
    # For non-SQLite URLs, enable pool_pre_ping to avoid stale connections
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=SQLALCHEMY_ECHO,
    )

# -------------------------------
# Session Factory
# -------------------------------

# expire_on_commit=False avoids attribute expiration on commit and is a better default for request-scoped sessions
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)

# -------------------------------
# FastAPI Dependency
# -------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session and ensure it's closed afterwards.

    Usage in FastAPI:
        dependencies=[Depends(get_db)]
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()