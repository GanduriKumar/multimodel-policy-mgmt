from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Iterable, Dict, Any

import uuid

from pydantic import BaseModel
from sqlalchemy import select, text
import sqlalchemy
from sqlalchemy.orm import Session

from app.models.decision_log import DecisionLog
from app.models.request_log import RequestLog
from app.models.policy import Policy
from app.models.policy_version import PolicyVersion
from app.models.evidence_item import EvidenceItem
from app.services.reports.canonicalization import to_canonical_json


class DecisionEvent(BaseModel):
    # ids
    tenant_id: int
    policy_id: Optional[int] = None
    policy_version_id: Optional[int] = None
    request_log_id: int
    decision_log_id: int

    # decision
    allowed: bool
    reasons: list[str] = []
    risk_score: Optional[int] = None
    evidence_present: bool = False

    # timestamps
    decided_at_utc: str
    decided_at_local: str
    local_timezone: str

    # integrity
    event_id: str
    canonical_json_sha256: str
    input_hash: str = ""
    evidence_ids: list[int] = []
    evidence_hashes: list[str] = []
    evidence_types: list[str] = []
    evidence_sources: list[str] = []

    # context
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    policy_name: Optional[str] = None


def _event_id() -> str:
    try:
        return str(uuid.uuid7())  # type: ignore[attr-defined]
    except Exception:
        return str(uuid.uuid4())


def _utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _rfc3339_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    s = dt.isoformat()
    return s[:-6] + "Z" if s.endswith("+00:00") else s


def _rfc3339_local(dt: datetime, tz: str) -> str:
    try:
        from zoneinfo import ZoneInfo  # type: ignore
        z = ZoneInfo(tz)
    except Exception:
        # Windows fallback: Asia/Kolkata -> UTC+05:30; else UTC
        if tz == "Asia/Kolkata":
            z = timezone(timedelta(hours=5, minutes=30))
        else:
            z = timezone.utc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(z).isoformat()


def _extract_evidence_ids(meta: Optional[dict]) -> list[int]:
    ids: list[int] = []
    if not isinstance(meta, dict):
        return ids
    raw = meta.get("evidence_ids")
    if isinstance(raw, list):
        for v in raw:
            try:
                val = int(v)
            except Exception:
                continue
            if val not in ids:
                ids.append(val)
    elif isinstance(raw, str):
        for part in raw.split(','):
            part = part.strip()
            if not part:
                continue
            try:
                val = int(part)
            except Exception:
                continue
            if val not in ids:
                ids.append(val)
    return ids


def _canonical_hash(payload: Dict[str, Any]) -> str:
    try:
        cj = to_canonical_json(payload)
        import hashlib
        return hashlib.sha256(cj.encode("utf-8")).hexdigest()
    except Exception:
        return ""


def list_decision_events(
    session: Session,
    *,
    tenant_id: int,
    from_utc: datetime,
    to_utc: datetime,
    tz: str = "Asia/Kolkata",
) -> List[DecisionEvent]:
    if from_utc.tzinfo is None:
        from_utc = from_utc.replace(tzinfo=timezone.utc)
    else:
        from_utc = from_utc.astimezone(timezone.utc)
    if to_utc.tzinfo is None:
        to_utc = to_utc.replace(tzinfo=timezone.utc)
    else:
        to_utc = to_utc.astimezone(timezone.utc)

    # Prefetch decisions in window for tenant
    try:
        decs = (
            session.execute(
                select(DecisionLog, RequestLog, Policy, PolicyVersion)
                .join(RequestLog, DecisionLog.request_log_id == RequestLog.id)
                .outerjoin(Policy, DecisionLog.policy_id == Policy.id)
                .outerjoin(PolicyVersion, DecisionLog.policy_version_id == PolicyVersion.id)
                .where(DecisionLog.tenant_id == tenant_id)
            )
            .all()
        )
    except sqlalchemy.exc.OperationalError as e:
        # Handle legacy databases that don't have the enhanced compliance audit columns
        msg = str(e).lower()
        if "reasoning_chain" in msg or "compliance_frameworks" in msg or "regulatory_mappings" in msg or \
           "engine_scores" in msg or "policy_version_snapshot" in msg or "no such column" in msg:
            # Add all missing enhanced compliance columns (SQLite supports ALTER TABLE ADD COLUMN)
            engine = session.get_bind()
            try:
                with engine.connect() as conn:
                    # Try to add each column - ignore errors if column already exists
                    columns_to_add = [
                        'ALTER TABLE decision_log ADD COLUMN reasoning_chain JSON',
                        'ALTER TABLE decision_log ADD COLUMN compliance_frameworks JSON',
                        'ALTER TABLE decision_log ADD COLUMN regulatory_mappings JSON',
                        'ALTER TABLE decision_log ADD COLUMN engine_scores JSON',
                        'ALTER TABLE decision_log ADD COLUMN policy_version_snapshot JSON',
                    ]
                    for alter_stmt in columns_to_add:
                        try:
                            conn.execute(text(alter_stmt))
                        except sqlalchemy.exc.OperationalError:
                            # Column might already exist, continue
                            pass
                    conn.commit()
            except Exception:
                # If we can't alter the table here, re-raise the original error to surface it.
                raise
            # Retry the original select after schema alteration
            decs = (
                session.execute(
                    select(DecisionLog, RequestLog, Policy, PolicyVersion)
                    .join(RequestLog, DecisionLog.request_log_id == RequestLog.id)
                    .outerjoin(Policy, DecisionLog.policy_id == Policy.id)
                    .outerjoin(PolicyVersion, DecisionLog.policy_version_id == PolicyVersion.id)
                    .where(DecisionLog.tenant_id == tenant_id)
                )
                .all()
            )
        else:
            raise

    events: list[DecisionEvent] = []

    for dec, req, pol, pver in decs:
        dtc = _utc_aware(dec.created_at)
        if not dtc or not (from_utc <= dtc <= to_utc):
            continue

        ev_ids = _extract_evidence_ids(getattr(req, "metadata_json", None))
        ev_items: list[EvidenceItem] = []
        ev_hashes: list[str] = []
        ev_types: list[str] = []
        ev_sources: list[str] = []
        if ev_ids:
            items = session.execute(select(EvidenceItem).where(EvidenceItem.id.in_(ev_ids))).scalars().all()
            for it in items:
                ev_items.append(it)
                ev_hashes.append((it.content_hash or ""))
                ev_types.append((it.evidence_type or ""))
                ev_sources.append((it.source or ""))

        base_payload = dict(
            tenant_id=dec.tenant_id,
            policy_id=dec.policy_id,
            policy_version_id=dec.policy_version_id,
            request_log_id=dec.request_log_id,
            decision_log_id=dec.id,
            allowed=bool(dec.allowed),
            reasons=list(dec.reasons or []),
            risk_score=dec.risk_score,
            evidence_present=bool(ev_ids),
            decided_at_utc=_rfc3339_utc(dtc),
            decided_at_local=_rfc3339_local(dtc, tz),
            local_timezone=tz,
            event_id=_event_id(),
            canonical_json_sha256="",
            input_hash=req.input_hash or "",
            evidence_ids=ev_ids,
            evidence_hashes=ev_hashes,
            evidence_types=ev_types,
            evidence_sources=ev_sources,
            request_id=req.request_id,
            client_ip=req.client_ip,
            user_agent=req.user_agent,
            policy_name=(pol.name if pol else None),
        )

        # Compute canonical hash (excluding itself)
        payload_for_hash = dict(base_payload)
        payload_for_hash.pop("canonical_json_sha256", None)
        base_payload["canonical_json_sha256"] = _canonical_hash(payload_for_hash)

        events.append(DecisionEvent(**base_payload))

    # Newest first
    events.sort(key=lambda e: e.decided_at_utc, reverse=True)
    return events
