"""
Evidence API routes.

Endpoints:
- POST /api/evidence           -> ingest new evidence
- GET  /api/evidence/{id}      -> retrieve stored evidence by id

Routes are thin and delegate to EvidenceRepo and Pydantic schemas.
"""

from __future__ import annotations

from typing import Any, Type, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from app.core.deps import get_evidence_repo
from app.core.contracts import EvidenceRepo
from app.schemas.evidence import EvidenceCreate, EvidenceOut


router = APIRouter(prefix="/api/evidence", tags=["evidence"])

T = TypeVar("T")


def _to_model(model_cls: Type[T], obj: Any) -> T:
    """
    Convert an ORM object to a Pydantic model, supporting both Pydantic v1 and v2.

    Handles SQLAlchemy reserved attribute name 'metadata' by mapping from
    EvidenceItem.metadata_json to schema field 'metadata'.
    """
    # Prefer Pydantic v2 direct validation
    model_validate = getattr(model_cls, "model_validate", None)
    if callable(model_validate):
        try:
            return model_validate(obj)  # type: ignore[misc]
        except Exception:
            # Fall through to manual mapping if validation fails (e.g., alias issues)
            pass

    # Manual mapping for EvidenceOut to avoid MetaData serialization issues
    try:
        from app.schemas.evidence import EvidenceOut as _EvidenceOut  # local import to avoid cycles
    except Exception:
        _EvidenceOut = None  # type: ignore

    if _EvidenceOut is not None and model_cls is _EvidenceOut:
        return model_cls(  # type: ignore[misc]
            id=getattr(obj, "id"),
            tenant_id=getattr(obj, "tenant_id"),
            policy_id=getattr(obj, "policy_id", None),
            policy_version_id=getattr(obj, "policy_version_id", None),
            evidence_type=getattr(obj, "evidence_type"),
            source=getattr(obj, "source", None),
            description=getattr(obj, "description", None),
            content_hash=getattr(obj, "content_hash", None),
            metadata=getattr(obj, "metadata_json", None),
            created_at=getattr(obj, "created_at"),
            updated_at=getattr(obj, "updated_at"),
        )

    # Pydantic v1
    from_orm = getattr(model_cls, "from_orm", None)
    if callable(from_orm):
        return from_orm(obj)  # type: ignore[misc]

    # Fallback: construct from dict
    if hasattr(obj, "__dict__"):
        data = dict(obj.__dict__)
        # Map metadata_json -> metadata if present
        if "metadata" not in data and "metadata_json" in data:
            data["metadata"] = data.get("metadata_json")
        return model_cls(**data)  # type: ignore[misc]
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
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error") from e

    # Convert ORM -> Pydantic with compatibility handler
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


class EvidenceDeleteRequest(BaseModel):
    evidence_ids: list[int] | None = None
    evidence_id: int | None = None


@router.delete("", status_code=status.HTTP_200_OK)
def delete_evidence(
    payload: EvidenceDeleteRequest,
    repo: EvidenceRepo = Depends(get_evidence_repo),
):
    """
    Delete evidence by id or a list of ids. Returns {"deleted": n}.

    Note: This simple route trusts the caller and does not enforce tenant scoping here.
    """
    ids: list[int] = []
    if payload.evidence_ids:
        ids.extend(int(i) for i in payload.evidence_ids if i)
    if payload.evidence_id:
        ids.append(int(payload.evidence_id))
    # De-dupe ids
    ids = sorted(set(ids))
    if not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No evidence ids provided")

    deleted = 0
    try:
        if hasattr(repo, "delete_evidence_bulk"):
            deleted = getattr(repo, "delete_evidence_bulk")(ids)  # type: ignore[attr-defined]
        elif hasattr(repo, "delete_evidence"):
            deleted = sum(1 if getattr(repo, "delete_evidence")(i) else 0 for i in ids)  # type: ignore[attr-defined]
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Delete not supported")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")
    return {"deleted": int(deleted)}
