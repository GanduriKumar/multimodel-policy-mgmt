"""
Evidence API routes.

Endpoints:
- POST /api/evidence           -> ingest new evidence
- GET  /api/evidence/{id}      -> retrieve stored evidence by id

Routes are thin and delegate to EvidenceRepo and Pydantic schemas.
"""

from __future__ import annotations

from typing import Any, Optional, Type, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.core.deps import get_evidence_repo
from app.core.contracts import EvidenceRepo
from app.schemas.evidence import EvidenceCreate, EvidenceOut


router = APIRouter(prefix="/api/evidence", tags=["evidence"])

T = TypeVar("T")


def _to_model(model_cls: Type[T], obj: Any) -> T:
    """
    Convert an ORM object to a Pydantic model, supporting both Pydantic v1 and v2.
    """
    # Pydantic v2
    model_validate = getattr(model_cls, "model_validate", None)
    if callable(model_validate):
        return model_validate(obj)  # type: ignore[misc]

    # Pydantic v1
    from_orm = getattr(model_cls, "from_orm", None)
    if callable(from_orm):
        return from_orm(obj)  # type: ignore[misc]

    # Fallback: construct from dict
    if hasattr(obj, "__dict__"):
        return model_cls(**obj.__dict__)  # type: ignore[misc]
    raise TypeError("Unsupported model conversion")


@router.post("", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
def create_evidence(
    payload: EvidenceCreate,
    tenant_id: int = Query(..., ge=1, description="Tenant identifier"),
    repo: EvidenceRepo = Depends(get_evidence_repo),
) -> EvidenceOut:
    """
    Ingest new evidence for a tenant.
    """
    # Prefer create_evidence if available (our SQLAlchemy repo), fall back to add_evidence (Protocol).
    try:
        if hasattr(repo, "create_evidence"):
            item = getattr(repo, "create_evidence")(  # type: ignore[attr-defined]
                tenant_id=tenant_id,
                evidence_type=payload.evidence_type,
                source=payload.source,
                description=payload.description,
                content_text=payload.content,
                metadata=payload.metadata,
                policy_id=payload.policy_id,
                policy_version_id=payload.policy_version_id,
            )
        else:
            # Protocol method signature (no automatic hash here)
            item = repo.add_evidence(
                tenant_id=tenant_id,
                evidence_type=payload.evidence_type,
                source=payload.source,
                description=payload.description,
                content_hash=None,
                metadata=payload.metadata,
                policy_id=payload.policy_id,
                policy_version_id=payload.policy_version_id,
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error") from e

    return _to_model(EvidenceOut, item)


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(
    evidence_id: int = Path(..., ge=1),
    repo: EvidenceRepo = Depends(get_evidence_repo),
) -> EvidenceOut:
    """
    Retrieve stored evidence by id.
    """
    # Prefer get_evidence if available (our SQLAlchemy repo), fall back to get_by_id (Protocol).
    item = None
    if hasattr(repo, "get_evidence"):
        item = getattr(repo, "get_evidence")(evidence_id)  # type: ignore[attr-defined]
    elif hasattr(repo, "get_by_id"):
        item = getattr(repo, "get_by_id")(evidence_id)  # type: ignore[attr-defined]

    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    return _to_model(EvidenceOut, item)
