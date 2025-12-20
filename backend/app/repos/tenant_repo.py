"""
SQLAlchemy-based Tenant repository.

Provides minimal operations:
- create_tenant(name, api_key_hash, is_active=True): creates a tenant with a generated unique slug
- get_by_api_key_hash(api_key_hash): fetch tenant by stored API key hash

Also implements a few common helpers compatible with the TenantRepo Protocol
(get_by_id, get_by_slug, list, update, delete, create) for broader use.
"""

from __future__ import annotations

import re
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.tenant import Tenant


__all__ = ["SqlAlchemyTenantRepo"]


def _slugify(name: str) -> str:
    """
    Convert a name into a URL-safe slug.
    Simple, deterministic: lowercase, alphanumerics and hyphens only.
    """
    base = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return base or "tenant"


class SqlAlchemyTenantRepo:
    """
    Concrete Tenant repository using SQLAlchemy ORM.

    Expects a Session provided by the caller (e.g., FastAPI dependency).
    """

    def __init__(self, session: Session) -> None:
        if not isinstance(session, Session):
            raise TypeError("session must be an instance of sqlalchemy.orm.Session")
        self.session = session

    # -------------------------------------------------
    # Minimal API requested by the task
    # -------------------------------------------------

    def create_tenant(self, name: str, api_key_hash: str, is_active: bool = True) -> Tenant:
        """
        Create a tenant with a generated unique slug and stored api_key_hash.

        The slug is generated from the name and made unique by appending a numeric suffix if needed.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(api_key_hash, str) or not api_key_hash.strip():
            raise ValueError("api_key_hash must be a non-empty string")

        # Generate a candidate slug and ensure uniqueness
        base = _slugify(name)
        slug = base
        idx = 2
        while self.get_by_slug(slug) is not None:
            slug = f"{base}-{idx}"
            idx += 1

        tenant = Tenant(
            name=name.strip(),
            slug=slug,
            api_key_hash=api_key_hash.strip().lower(),
            is_active=bool(is_active),
        )
        self.session.add(tenant)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            # Likely name or api_key_hash unique conflict
            raise ValueError("Tenant creation failed due to uniqueness constraint") from exc
        self.session.refresh(tenant)
        return tenant

    def get_by_api_key_hash(self, api_key_hash: str) -> Optional[Tenant]:
        """
        Return tenant by API key hash (case-insensitive for hex strings).
        """
        if not isinstance(api_key_hash, str) or not api_key_hash.strip():
            return None
        stmt = select(Tenant).where(Tenant.api_key_hash == api_key_hash.strip().lower())
        return self.session.execute(stmt).scalars().first()

    # -------------------------------------------------
    # Convenience methods aligned with TenantRepo Protocol
    # -------------------------------------------------

    def get_by_id(self, tenant_id: int) -> Optional[Tenant]:
        return self.session.get(Tenant, int(tenant_id))

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        stmt = select(Tenant).where(Tenant.slug == slug)
        return self.session.execute(stmt).scalars().first()

    def list(self, offset: int = 0, limit: int = 50) -> Sequence[Tenant]:
        stmt = (
            select(Tenant)
            .order_by(Tenant.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, limit))
        )
        return list(self.session.execute(stmt).scalars().all())

    def create(self, name: str, slug: str, description: Optional[str] = None, is_active: bool = True) -> Tenant:
        tenant = Tenant(name=name.strip(), slug=slug.strip(), description=description, is_active=bool(is_active))
        self.session.add(tenant)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ValueError("Tenant creation failed due to uniqueness constraint") from exc
        self.session.refresh(tenant)
        return tenant

    def update(self, tenant: Tenant, **fields) -> Tenant:
        for k, v in fields.items():
            if hasattr(tenant, k):
                setattr(tenant, k, v)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ValueError("Tenant update failed due to uniqueness constraint") from exc
        self.session.refresh(tenant)
        return tenant

    def delete(self, tenant: Tenant) -> None:
        self.session.delete(tenant)
        self.session.commit()
