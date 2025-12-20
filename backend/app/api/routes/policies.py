"""
Policy management API routes.

Endpoints:
- POST   /api/policies                             -> create a policy
- GET    /api/policies                             -> list policies (by tenant_id)
- POST   /api/policies/{policy_id}/versions        -> add a policy version
- POST   /api/policies/{policy_id}/versions/{ver}/activate -> activate a version

Routes are thin: they delegate to a PolicyRepo and return Pydantic schemas.
"""

from __future__ import annotations

from typing import Any, Sequence, Type, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status

from app.core.contracts import PolicyRepo
from app.core.deps import get_policy_repo
from app.schemas.policies import (
    PolicyCreate,
    PolicyOut,
    PolicyListResponse,
    PolicyVersionCreate,
    PolicyVersionOut,
)

router = APIRouter(prefix="/api/policies", tags=["policies"])

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

    # Fallback: construct from dict if possible
    if hasattr(obj, "__dict__"):
        return model_cls(**obj.__dict__)  # type: ignore[misc]
    raise TypeError("Unsupported model conversion")


@router.post("", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    repo: PolicyRepo = Depends(get_policy_repo),
) -> PolicyOut:
    """
    Create a new policy.
    """
    try:
        policy = repo.create_policy(
            tenant_id=payload.tenant_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            is_active=payload.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return _to_model(PolicyOut, policy)


@router.get("", response_model=PolicyListResponse)
def list_policies(
    tenant_id: int = Query(..., ge=1, description="Tenant identifier"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    repo: PolicyRepo = Depends(get_policy_repo),
) -> PolicyListResponse:
    """
    List policies for a tenant (paginated).
    """
    items = repo.list_policies(tenant_id=tenant_id, offset=offset, limit=limit)
    items_out = [_to_model(PolicyOut, p) for p in items]
    return PolicyListResponse(items=items_out, total=len(items_out))


@router.post("/{policy_id}/versions", response_model=PolicyVersionOut, status_code=status.HTTP_201_CREATED)
def add_policy_version(
    policy_id: int = Path(..., ge=1),
    payload: PolicyVersionCreate = ...,
    repo: PolicyRepo = Depends(get_policy_repo),
) -> PolicyVersionOut:
    """
    Add a new version to a policy.

    Note: If payload.policy_id is provided and does not match the path parameter,
    a 400 error is returned.
    """
    if payload.policy_id is not None and int(payload.policy_id) != int(policy_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="policy_id in body does not match path parameter",
        )

    try:
        version = repo.add_version(
            policy_id=policy_id,
            document=payload.document,
            is_active=payload.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return _to_model(PolicyVersionOut, version)


@router.post("/{policy_id}/versions/{version}/activate", response_model=PolicyVersionOut)
def activate_policy_version(
    policy_id: int = Path(..., ge=1),
    version: int = Path(..., ge=1),
    repo: PolicyRepo = Depends(get_policy_repo),
) -> PolicyVersionOut:
    """
    Activate a specific version for a policy (deactivates others).
    Uses set_active_version if provided by the repository; falls back to activate_version.
    """
    try:
        # Prefer Protocol method name if available
        if hasattr(repo, "set_active_version"):
            pv = repo.set_active_version(policy_id, version)  # type: ignore[attr-defined]
        elif hasattr(repo, "activate_version"):
            pv = repo.activate_version(policy_id, version)  # type: ignore[attr-defined]
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Repository does not support version activation",
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return _to_model(PolicyVersionOut, pv)