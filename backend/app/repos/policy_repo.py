"""
SQLAlchemy-based Policy repository implementation.

Implements core operations:
- create_policy
- list_policies
- add_version
- activate_version (ensures only one active version per policy)
- get_active_policy_doc (returns the active version's document as dict)

This repository expects a SQLAlchemy Session to be provided by the caller.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.policy_version import PolicyVersion


class SqlAlchemyPolicyRepo:
    """
    Concrete Policy repository using SQLAlchemy ORM.
    """

    def __init__(self, session: Session) -> None:
        if not isinstance(session, Session):
            raise TypeError("session must be an instance of sqlalchemy.orm.Session")
        self.session = session

    # -------------------------------
    # Policies
    # -------------------------------

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
        policy = Policy(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            description=description,
            is_active=is_active,
        )
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    def list_policies(self, tenant_id: int, offset: int = 0, limit: int = 50) -> Sequence[Policy]:
        """
        List policies for a tenant with pagination.
        """
        stmt = (
            select(Policy)
            .where(Policy.tenant_id == tenant_id)
            .order_by(Policy.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, limit))
        )
        return list(self.session.execute(stmt).scalars().all())

    # -------------------------------
    # Policy Versions
    # -------------------------------

    def add_version(self, policy_id: int, document: dict, is_active: bool = True) -> PolicyVersion:
        """
        Create a new PolicyVersion for the given policy.
        - Version number is assigned as (max existing + 1), starting at 1.
        - If is_active is True, marks all other versions inactive.
        """
        # Ensure policy exists
        policy = self.session.get(Policy, policy_id)
        if policy is None:
            raise ValueError(f"Policy id={policy_id} not found")

        # Determine next version number
        max_stmt = select(func.max(PolicyVersion.version)).where(PolicyVersion.policy_id == policy_id)
        current_max = self.session.execute(max_stmt).scalar()
        next_version = int(current_max or 0) + 1

        # Optionally deactivate existing versions
        if is_active:
            self.session.execute(
                update(PolicyVersion)
                .where(PolicyVersion.policy_id == policy_id, PolicyVersion.is_active.is_(True))
                .values(is_active=False)
            )

        pv = PolicyVersion(
            policy_id=policy_id,
            version=next_version,
            document=document,
            is_active=is_active,
        )
        self.session.add(pv)
        self.session.commit()
        self.session.refresh(pv)
        return pv

    def activate_version(self, policy_id: int, version: int) -> PolicyVersion:
        """
        Activate a specific version for the given policy.
        Ensures all other versions are deactivated.
        """
        # Lookup target version
        stmt = select(PolicyVersion).where(
            PolicyVersion.policy_id == policy_id, PolicyVersion.version == version
        )
        target = self.session.execute(stmt).scalars().first()
        if target is None:
            raise ValueError(f"PolicyVersion policy_id={policy_id} version={version} not found")

        # Deactivate others, activate target
        self.session.execute(
            update(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id, PolicyVersion.id != target.id)
            .values(is_active=False)
        )
        self.session.execute(
            update(PolicyVersion)
            .where(PolicyVersion.id == target.id)
            .values(is_active=True)
        )
        self.session.commit()
        # Refresh and return
        self.session.refresh(target)
        return target

    # -------------------------------
    # Accessors
    # -------------------------------

    def get_active_policy_doc(self, tenant_id: int, policy_slug: str) -> Optional[dict]:
        """
        Return the active policy document (dict) for the tenant's policy slug, or None if not found.
        """
        # Find policy
        pol_stmt = select(Policy).where(Policy.tenant_id == tenant_id, Policy.slug == policy_slug)
        policy = self.session.execute(pol_stmt).scalars().first()
        if policy is None:
            return None

        # Get active version
        ver_stmt = select(PolicyVersion).where(
            PolicyVersion.policy_id == policy.id, PolicyVersion.is_active.is_(True)
        ).order_by(PolicyVersion.version.desc())
        active = self.session.execute(ver_stmt).scalars().first()
        if active is None:
            return None

        return dict(active.document or {})