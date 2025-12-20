"""
SQLAlchemy-based Evidence repository.

Implements operations:
- create_evidence: persists an EvidenceItem, computing a deterministic content_hash
                   using app.core.hashing.sha256_text when possible
- get_evidence: fetch a single EvidenceItem by primary key
- list_evidence_by_ids: fetch multiple EvidenceItems by their ids
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
            # Canonical JSON to ensure deterministic hashing
            canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            return sha256_text(canonical)
        return None

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
        # Validate required args
        if not isinstance(tenant_id, int):
            raise TypeError("tenant_id must be an int")
        if not isinstance(evidence_type, str) or not evidence_type.strip():
            raise ValueError("evidence_type must be a non-empty string")

        # Compute hash
        content_hash = self._compute_content_hash(
            content_text=content_text, source=source, description=description, metadata=metadata
        )

        # Deduplicate if possible (unique constraint tenant_id + content_hash)
        if content_hash:
            stmt = select(EvidenceItem).where(
                EvidenceItem.tenant_id == tenant_id, EvidenceItem.content_hash == content_hash
            )
            existing = self.session.execute(stmt).scalars().first()
            if existing is not None:
                return existing

        # Create and persist
        item = EvidenceItem(
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            evidence_type=evidence_type.strip(),
            source=source,
            description=description,
            content_hash=content_hash,
            metadata=metadata,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get_evidence(self, evidence_id: int) -> Optional[EvidenceItem]:
        """
        Return an EvidenceItem by its primary key, or None if not found.
        """
        if not isinstance(evidence_id, int):
            raise TypeError("evidence_id must be an int")
        return self.session.get(EvidenceItem, evidence_id)

    def list_evidence_by_ids(self, ids: Sequence[int]) -> Sequence[EvidenceItem]:
        """
        Return all EvidenceItem rows whose id is in the provided list (order not guaranteed).
        """
        # Guard against empty input to avoid SQL 'IN ()' issues
        ids = [int(i) for i in ids if isinstance(i, int) or (isinstance(i, str) and str(i).isdigit())]
        if not ids:
            return []

        stmt = select(EvidenceItem).where(EvidenceItem.id.in_(ids))
        return list(self.session.execute(stmt).scalars().all())