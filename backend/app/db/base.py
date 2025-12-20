"""
SQLAlchemy declarative base and model import hook.

- Base: Declarative base class for all ORM models.
- import_all_models(): Dynamically imports all modules under app.models to register mappers.

Why import models here?
SQLAlchemy needs model classes to be imported at least once so their tables are
registered on the metadata. This module provides a safe utility to import all
model modules without hard-coding their names.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import List

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

__all__ = ["Base", "import_all_models"]


# -------------------------------
# Declarative Base with conventions
# -------------------------------

# Naming conventions for constraints & indexes (helpful for migrations)
_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    # Attach a metadata object with naming conventions
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)

    # Provide a default table name (lowercase class name) if not explicitly set
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


# -------------------------------
# Dynamic model import
# -------------------------------

def import_all_models() -> List[str]:
    """
    Import all modules under app.models so SQLAlchemy registers all model tables.

    Returns:
        A list of fully-qualified module names that were successfully imported.
    """
    imported: list[str] = []
    try:
        # Import the package; may raise if the package doesn't exist
        models_pkg = importlib.import_module("app.models")
    except ModuleNotFoundError:
        # No models package yet; not an error
        return imported

    # Walk through all submodules in app.models and import them
    if hasattr(models_pkg, "__path__"):
        prefix = models_pkg.__name__ + "."
        for finder, name, ispkg in pkgutil.walk_packages(models_pkg.__path__, prefix):
            try:
                importlib.import_module(name)
                imported.append(name)
            except Exception:
                # Best-effort import: ignore modules that fail to import,
                # keeping base usable even if some models have issues.
                continue

    return imported


# Auto-import models on module load (safe even if none exist)
try:
    _IMPORTED_MODELS = import_all_models()
except Exception:
    # Never fail base initialization due to import-time errors
    _IMPORTED_MODELS = []