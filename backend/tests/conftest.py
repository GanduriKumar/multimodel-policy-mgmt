"""
Pytest configuration for backend tests.

Provides an isolated SQLite database per test run using a temporary file
(rather than in-memory) to support multiple connections and sessions.

Fixtures:
- db_engine (session scope): Creates the engine, builds tables, and tears down.
- db_session (function scope): Provides a clean Session per test, with FK enabled.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Generator

import pytest


# Ensure the 'backend' directory is on sys.path so we can import app modules when running tests from repo root
CURRENT_DIR = Path(__file__).parent
BACKEND_ROOT = (CURRENT_DIR / "..").resolve()
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session")
def db_engine(tmp_path_factory) -> "Generator":
    """
    Create a temporary file-based SQLite engine for the entire test session.
    Sets DATABASE_URL before importing the session module so it picks up this DB.
    """
    tmp_dir = tmp_path_factory.mktemp("db")
    db_file = tmp_dir / "test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    # Configure environment for the app's DB module
    os.environ["DATABASE_URL"] = db_url
    os.environ.setdefault("SQLALCHEMY_ECHO", "0")

    # Import after setting env vars so the module uses our test DB URL
    from app.db.session import engine  # type: ignore
    from app.db.base import Base, import_all_models  # type: ignore

    # Ensure models are imported and tables are created
    import_all_models()
    Base.metadata.create_all(bind=engine)

    try:
        yield engine
    finally:
        # Drop all tables and dispose engine
        try:
            Base.metadata.drop_all(bind=engine)
        except Exception:
            # Best-effort teardown
            pass
        try:
            engine.dispose()
        except Exception:
            pass
        # Cleanup DB file
        try:
            if db_file.exists():
                db_file.unlink()
        except Exception:
            pass


@pytest.fixture(scope="function")
def db_session(db_engine) -> "Generator":
    """
    Provide a fresh Session for each test function.
    Enables foreign keys and truncates tables before each test for isolation.
    """
    from sqlalchemy import text  # type: ignore
    from app.db.session import SessionLocal  # type: ignore
    from app.db.base import Base  # type: ignore

    session = SessionLocal()

    # Enable SQLite foreign key enforcement
    try:
        session.execute(text("PRAGMA foreign_keys = ON"))
    except Exception:
        # Non-fatal if pragma fails (e.g., non-SQLite URL), but we expect SQLite here.
        pass

    # Truncate all tables before running the test (clean slate)
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    except Exception:
        session.rollback()
        raise

    try:
        yield session
    finally:
        # Rollback any uncommitted work and close
        try:
            session.rollback()
        except Exception:
            pass
        finally:
            session.close()