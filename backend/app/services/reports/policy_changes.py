"""
Policy Changes events enumeration service.

Produces normalized events for Policy and PolicyVersion changes for a tenant
in an inclusive UTC time window. Timestamps returned as RFC3339 strings in
UTC and Asia/Kolkata. Uses policy_id only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

import hashlib
import json
import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.policy_version import PolicyVersion


class PolicyChangeEvent(BaseModel):
    tenant_id: int
    policy_id: int
    policy_name: str
    version_id: Optional[int] = None
    version: Optional[int] = None
    is_active: Optional[bool] = None
    change_type: str
    changed_by: str
    changed_at_utc: str
    changed_at_local: str
    local_timezone: str
    event_id: str
    document_sha256: str
    diff_summary: str = ""


def _rfc3339_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    s = dt.isoformat()
    # Ensure Z suffix
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    return s


def _rfc3339_local(dt: datetime, tz: str) -> str:
    from zoneinfo import ZoneInfo

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_local = dt.astimezone(ZoneInfo(tz))
    return dt_local.isoformat()


def _sha256_document(doc: Optional[dict]) -> str:
    if not isinstance(doc, dict):
        return ""
    try:
        data = json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return ""


def list_policy_change_events(
    session: Session,
    *,
    tenant_id: int,
    from_utc: datetime,
    to_utc: datetime,
    tz: str = "Asia/Kolkata",
) -> List[PolicyChangeEvent]:
    """
    Enumerate policy and version change events for a tenant within [from_utc, to_utc] inclusive.
    """
    if from_utc.tzinfo is None:
        from_utc = from_utc.replace(tzinfo=timezone.utc)
    else:
        from_utc = from_utc.astimezone(timezone.utc)
    if to_utc.tzinfo is None:
        to_utc = to_utc.replace(tzinfo=timezone.utc)
    else:
        to_utc = to_utc.astimezone(timezone.utc)

    events: List[PolicyChangeEvent] = []

    # Fetch policies for tenant that have created/updated in window
    pols = session.execute(
        select(Policy).where(Policy.tenant_id == tenant_id)
    ).scalars().all()

    # Build a dict policy_id -> policy to help joins
    pol_by_id = {p.id: p for p in pols}

    # Policy-level events
    for p in pols:
        # policy_created
        if p.created_at and from_utc <= p.created_at <= to_utc:
            events.append(
                PolicyChangeEvent(
                    tenant_id=p.tenant_id,
                    policy_id=p.id,
                    policy_name=p.name,
                    change_type="policy_created",
                    changed_by="Unknown",
                    changed_at_utc=_rfc3339_utc(p.created_at),
                    changed_at_local=_rfc3339_local(p.created_at, tz),
                    local_timezone=tz,
                    event_id=str(uuid.uuid7()),
                    document_sha256="",
                )
            )
        # policy_updated / activated / deactivated (heuristics)
        if p.updated_at and from_utc <= p.updated_at <= to_utc:
            # We emit policy_updated always when updated_at in range
            events.append(
                PolicyChangeEvent(
                    tenant_id=p.tenant_id,
                    policy_id=p.id,
                    policy_name=p.name,
                    change_type="policy_updated",
                    changed_by="Unknown",
                    changed_at_utc=_rfc3339_utc(p.updated_at),
                    changed_at_local=_rfc3339_local(p.updated_at, tz),
                    local_timezone=tz,
                    event_id=str(uuid.uuid7()),
                    document_sha256="",
                )
            )
            # Activation status snapshot at updated_at (we don't know previous value without history)
            events.append(
                PolicyChangeEvent(
                    tenant_id=p.tenant_id,
                    policy_id=p.id,
                    policy_name=p.name,
                    change_type=("policy_activated" if p.is_active else "policy_deactivated"),
                    changed_by="Unknown",
                    changed_at_utc=_rfc3339_utc(p.updated_at),
                    changed_at_local=_rfc3339_local(p.updated_at, tz),
                    local_timezone=tz,
                    event_id=str(uuid.uuid7()),
                    document_sha256="",
                )
            )

    # Version-level events
    vers = session.execute(
        select(PolicyVersion).where(PolicyVersion.policy_id.in_(list(pol_by_id.keys())))
    ).scalars().all()

    # Group versions by policy
    vers_by_policy: dict[int, list[PolicyVersion]] = {}
    for v in vers:
        vers_by_policy.setdefault(v.policy_id, []).append(v)

    for policy_id, vlist in vers_by_policy.items():
        p = pol_by_id.get(policy_id)
        pname = p.name if p else f"policy:{policy_id}"

        # version_created
        for v in vlist:
            if v.created_at and from_utc <= v.created_at <= to_utc:
                events.append(
                    PolicyChangeEvent(
                        tenant_id=p.tenant_id if p else 0,
                        policy_id=policy_id,
                        policy_name=pname,
                        version_id=v.id,
                        version=v.version,
                        is_active=v.is_active,
                        change_type="version_created",
                        changed_by="Unknown",
                        changed_at_utc=_rfc3339_utc(v.created_at),
                        changed_at_local=_rfc3339_local(v.created_at, tz),
                        local_timezone=tz,
                        event_id=str(uuid.uuid7()),
                        document_sha256=_sha256_document(getattr(v, "document", None)),
                    )
                )

        # Activation toggles: we only have updated_at on the activated version; infer deactivation for others
        # Find versions with updated_at in range and is_active True -> activation at that time
        for v in vlist:
            if v.updated_at and from_utc <= v.updated_at <= to_utc and v.is_active:
                # Activated event for this version
                events.append(
                    PolicyChangeEvent(
                        tenant_id=p.tenant_id if p else 0,
                        policy_id=policy_id,
                        policy_name=pname,
                        version_id=v.id,
                        version=v.version,
                        is_active=True,
                        change_type="version_activated",
                        changed_by="Unknown",
                        changed_at_utc=_rfc3339_utc(v.updated_at),
                        changed_at_local=_rfc3339_local(v.updated_at, tz),
                        local_timezone=tz,
                        event_id=str(uuid.uuid7()),
                        document_sha256=_sha256_document(getattr(v, "document", None)),
                    )
                )
                # Infer deactivation for all other versions at the same timestamp
                for ov in vlist:
                    if ov.id == v.id:
                        continue
                    events.append(
                        PolicyChangeEvent(
                            tenant_id=p.tenant_id if p else 0,
                            policy_id=policy_id,
                            policy_name=pname,
                            version_id=ov.id,
                            version=ov.version,
                            is_active=False,
                            change_type="version_deactivated",
                            changed_by="Unknown",
                            changed_at_utc=_rfc3339_utc(v.updated_at),
                            changed_at_local=_rfc3339_local(v.updated_at, tz),
                            local_timezone=tz,
                            event_id=str(uuid.uuid7()),
                            document_sha256=_sha256_document(getattr(ov, "document", None)),
                        )
                    )

    # Sort newest first by changed_at_utc
    events.sort(key=lambda e: e.changed_at_utc, reverse=True)
    return events
