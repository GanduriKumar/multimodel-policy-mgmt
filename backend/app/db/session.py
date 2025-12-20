"""
SQLAlchemy session setup for SQLite, with a FastAPI-compatible dependency.

- ENGINE: Synchronous engine using SQLite by default.
- SessionLocal: sessionmaker factory bound to the engine.
- get_db(): Generator that yields a session and ensures it is closed.

Environment variables:
- DATABASE_URL: Full SQLAlchemy URL (default: sqlite:///./app.db)
- SQLALCHEMY_ECHO: "1" or "true" to enable SQL echo (default: off)
"""

from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

__all__ = ["engine", "SessionLocal", "get_db", "DATABASE_URL"]

# -------------------------------
# Configuration
# -------------------------------

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
SQLALCHEMY_ECHO: bool = os.getenv("SQLALCHEMY_ECHO", "0").lower() in {"1", "true", "yes", "on"}

# -------------------------------
# Engine
# -------------------------------

# SQLite needs "check_same_thread=False" for multithreaded apps (e.g., FastAPI with Uvicorn)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=SQLALCHEMY_ECHO,
        future=True,
    )
else:
    # For non-SQLite URLs, enable pool_pre_ping to avoid stale connections
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=SQLALCHEMY_ECHO,
        future=True,
    )

# -------------------------------
# Session Factory
# -------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
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