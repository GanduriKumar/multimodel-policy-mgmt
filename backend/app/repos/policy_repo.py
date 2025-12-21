"""
SQLAlchemy-based Policy repository.

Implements policy and version CRUD aligned with the PolicyRepo Protocol:
- get_by_slug, list_policies, create_policy, update_policy
- add_version (auto-increment), set_active_version (deactivate others)
- get_active_version, get_version, list_versions
- convenience: get_policy_by_id, get_active_policy_doc
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.policy_version import PolicyVersion


__all__ = ["SqlAlchemyPolicyRepo"]


class SqlAlchemyPolicyRepo:
    """
    Concrete Policy repository using SQLAlchemy ORM.
    """

    def __init__(self, session: Session) -> None:
        if not isinstance(session, Session):
            raise TypeError("session must be an instance of sqlalchemy.orm.Session")
        self.session = session

    # -------------------------------
    # Policy operations
    # -------------------------------

    def get_policy_by_id(self, policy_id: int) -> Optional[Policy]:
        stmt = select(Policy).where(Policy.id == policy_id)
        return self.session.execute(stmt).scalars().first()

    def get_by_slug(self, tenant_id: int, slug: str) -> Optional[Policy]:
        if not isinstance(tenant_id, int):
            raise TypeError("tenant_id must be an int")
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError("slug must be a non-empty string")
        stmt = select(Policy).where(Policy.tenant_id == tenant_id, Policy.slug == slug.strip())
        return self.session.execute(stmt).scalars().first()

    def list_policies(self, tenant_id: int, offset: int = 0, limit: int = 50) -> Sequence[Policy]:
        if not isinstance(tenant_id, int):
            raise TypeError("tenant_id must be an int")
        stmt = (
            select(Policy)
            .where(Policy.tenant_id == tenant_id)
            .order_by(Policy.created_at.desc())
            .offset(max(0, int(offset)))
            .limit(max(1, int(limit)))
        )
        return list(self.session.execute(stmt).scalars().all())

    def create_policy(
        self,
        tenant_id: int,
        name: str,
        slug: str,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> Policy:
        """
        Create and persist a new Policy.
        """
        if not isinstance(tenant_id, int):
            raise TypeError("tenant_id must be an int")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError("slug must be a non-empty string")

        policy = Policy(
            tenant_id=tenant_id,
            name=name.strip(),
            slug=slug.strip(),
            description=description,
            is_active=bool(is_active),
        )
        self.session.add(policy)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ValueError("Policy creation failed due to uniqueness constraint") from exc
        self.session.refresh(policy)
        return policy

    def update_policy(
        self,
        policy_id: int,
        *,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Policy:
        """
        Update mutable fields on a Policy.
        """
        policy = self.get_policy_by_id(policy_id)
        if policy is None:
            raise ValueError("Policy not found")

        if name is not None:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("name must be a non-empty string")
            policy.name = name.strip()
        if slug is not None:
            if not isinstance(slug, str) or not slug.strip():
                raise ValueError("slug must be a non-empty string")
            policy.slug = slug.strip()
        if description is not None:
            policy.description = description
        if is_active is not None:
            policy.is_active = bool(is_active)

        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ValueError("Policy update failed due to uniqueness constraint") from exc
        self.session.refresh(policy)
        return policy

    # -------------------------------
    # Version operations
    # -------------------------------

    def _next_version_number(self, policy_id: int) -> int:
        stmt = select(func.max(PolicyVersion.version)).where(PolicyVersion.policy_id == policy_id)
        current_max = self.session.execute(stmt).scalar()
        return int(current_max or 0) + 1

    def add_version(self, policy_id: int, document: dict, is_active: bool = True) -> PolicyVersion:
        """
        Create a new policy version with auto-incremented version number.
        Optionally mark it active (deactivates others for this policy).
        """
        if not isinstance(document, dict):
            raise ValueError("document must be a dict")
        policy = self.get_policy_by_id(policy_id)
        if policy is None:
            raise ValueError("Policy not found")

        next_ver = self._next_version_number(policy_id)
        pv = PolicyVersion(policy_id=policy_id, version=next_ver, document=dict(document), is_active=bool(is_active))
        self.session.add(pv)

        if is_active:
            # Deactivate other versions for the policy in one statement; the new row is not yet committed
            self.session.flush()
            self.session.execute(
                update(PolicyVersion)
                .where(PolicyVersion.policy_id == policy_id, PolicyVersion.id != pv.id)
                .values(is_active=False)
            )

        self.session.commit()
        self.session.refresh(pv)
        return pv

    def set_active_version(self, policy_id: int, version: int) -> PolicyVersion:
        """
        Set the specified version as active and deactivate all other versions for that policy.
        """
        pv = self.get_version(policy_id, version)
        if pv is None:
            raise ValueError("Policy version not found")

        # Activate selected
        pv.is_active = True
        self.session.flush()

        # Deactivate others
        self.session.execute(
            update(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id, PolicyVersion.id != pv.id)
            .values(is_active=False)
        )

        self.session.commit()
        self.session.refresh(pv)
        return pv

    # Backward-compatible alias used by tests/fakes
    def activate_version(self, policy_id: int, version: int) -> PolicyVersion:
        """Alias for set_active_version to maintain API compatibility."""
        return self.set_active_version(policy_id, version)

    def get_active_version(self, policy_id: int) -> Optional[PolicyVersion]:
        stmt = select(PolicyVersion).where(PolicyVersion.policy_id == policy_id, PolicyVersion.is_active.is_(True))
        return self.session.execute(stmt).scalars().first()

    def get_version(self, policy_id: int, version: int) -> Optional[PolicyVersion]:
        stmt = select(PolicyVersion).where(
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.version == int(version),
        )
        return self.session.execute(stmt).scalars().first()

    def list_versions(self, policy_id: int, offset: int = 0, limit: int = 50) -> Sequence[PolicyVersion]:
        stmt = (
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id)
            .order_by(PolicyVersion.version.desc())
            .offset(max(0, int(offset)))
            .limit(max(1, int(limit)))
        )
        return list(self.session.execute(stmt).scalars().all())

    # -------------------------------
    # Convenience
    # -------------------------------

    def get_active_policy_doc(self, tenant_id: int, policy_slug: str) -> Optional[dict]:
        """
        Return the active policy document (dict) for the tenant's policy slug, or None if not found.
        """
        pol = self.get_by_slug(tenant_id, policy_slug)
        if not pol:
            return None
        pv = self.get_active_version(pol.id)
        return dict(pv.document) if pv else None