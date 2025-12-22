"""
SQLAlchemy-based Evidence repository.

Implements:
- create_evidence: compute deterministic content_hash and dedupe by (tenant_id, content_hash)
- add_evidence: legacy API (accepts content_hash; computes when missing for convenience)
- get_evidence / get_by_id: fetch by primary key
- get_by_ids: batch fetch helper
"""

from __future__ import annotations

import json
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hashing import sha256_text
from app.models.evidence_item import EvidenceItem


__all__ = ["SqlAlchemyEvidenceRepo"]


class SqlAlchemyEvidenceRepo:
    """
    Concrete Evidence repository using SQLAlchemy ORM.
    """

    def __init__(self, session: Session) -> None:
        if not isinstance(session, Session):
            raise TypeError("session must be an instance of sqlalchemy.orm.Session")
        self.session = session

    # -------------------------------
    # Helpers
    # -------------------------------

    def _compute_content_hash(
        self,
        *,
        content_text: Optional[str],
        source: Optional[str],
        description: Optional[str],
        metadata: Optional[dict],
    ) -> Optional[str]:
        """
        Compute a deterministic content hash using sha256_text.

        Priority of inputs for hashing:
        1) content_text (if provided)
        2) source (if provided)
        3) description (if provided)
        4) metadata (JSON-serialized with sorted keys) (if provided)
        If none available, returns None.
        """
        if content_text:
            return sha256_text(content_text)
        if source:
            return sha256_text(source)
        if description:
            return sha256_text(description)
        if metadata is not None:
            canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            return sha256_text(canonical)
        return None

    # -------------------------------
    # CRUD
    # -------------------------------

    def create_evidence(
        self,
        *,
        tenant_id: int,
        evidence_type: str,
        source: Optional[str] = None,
        description: Optional[str] = None,
        content_text: Optional[str] = None,
        metadata: Optional[dict] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
    ) -> EvidenceItem:
        """
        Create and persist an EvidenceItem.

        - Computes content_hash using sha256_text over the best-available input.
        - If an item with the same (tenant_id, content_hash) exists and a hash is computed,
          returns the existing item instead of creating a duplicate.
        """
        if not isinstance(tenant_id, int):
            raise TypeError("tenant_id must be an int")
        if not isinstance(evidence_type, str) or not evidence_type.strip():
            raise ValueError("evidence_type must be a non-empty string")

        content_hash = self._compute_content_hash(
            content_text=content_text, source=source, description=description, metadata=metadata
        )

        # Deduplicate if possible when a hash exists
        if content_hash:
            existing = (
                self.session.execute(
                    select(EvidenceItem).where(
                        EvidenceItem.tenant_id == tenant_id,
                        EvidenceItem.content_hash == content_hash,
                    )
                )
                .scalars()
                .first()
            )
            if existing is not None:
                return existing

        item = EvidenceItem(
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            evidence_type=evidence_type.strip(),
            source=source,
            description=description,
            content_hash=content_hash,
            metadata_json=metadata,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    # Legacy/Protocol method (content_hash provided by caller; we compute if not given for convenience)
    def add_evidence(
        self,
        tenant_id: int,
        evidence_type: str,
        source: Optional[str] = None,
        description: Optional[str] = None,
        content_hash: Optional[str] = None,
        metadata: Optional[dict] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
    ) -> EvidenceItem:
        if not content_hash:
            content_hash = self._compute_content_hash(
                content_text=None, source=source, description=description, metadata=metadata
            )
        # If we have a hash, dedupe
        if content_hash:
            existing = (
                self.session.execute(
                    select(EvidenceItem).where(
                        EvidenceItem.tenant_id == tenant_id,
                        EvidenceItem.content_hash == content_hash,
                    )
                )
                .scalars()
                .first()
            )
            if existing is not None:
                return existing

        item = EvidenceItem(
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            evidence_type=evidence_type.strip(),
            source=source,
            description=description,
            content_hash=content_hash,
            metadata_json=metadata,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get_evidence(self, evidence_id: int) -> Optional[EvidenceItem]:
        """
        Return an EvidenceItem by its primary key, or None if not found.
        """
        stmt = select(EvidenceItem).where(EvidenceItem.id == int(evidence_id))
        return self.session.execute(stmt).scalars().first()

    # Fallback alias used by some routes
    def get_by_id(self, evidence_id: int) -> Optional[EvidenceItem]:
        return self.get_evidence(evidence_id)

    # Optional helper
    def get_by_ids(self, evidence_ids: Sequence[int]) -> Sequence[EvidenceItem]:
        if not evidence_ids:
            return []
        stmt = select(EvidenceItem).where(EvidenceItem.id.in_([int(i) for i in evidence_ids]))
        return list(self.session.execute(stmt).scalars().all())