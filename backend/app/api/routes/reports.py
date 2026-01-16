from __future__ import annotations

from datetime import datetime
from typing import Optional
import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.deps import get_policy_repo, get_audit_repo, get_evidence_repo, get_db, get_api_key
from sqlalchemy.orm import Session

from app.services.reports.timeutils import compute_range, fmt_rfc3339_utc
from app.services.reports.policy_changes import list_policy_change_events
from app.services.reports.renderers import to_csv as pol_to_csv, to_ndjson as pol_to_ndjson, to_json_array as pol_to_json
from app.services.reports.decisions import list_decision_events
from app.services.reports.decisions_renderers import to_csv as dec_to_csv, to_ndjson as dec_to_ndjson, to_json_array as dec_to_json
from app.services.reports.html_renderer import render_policy_changes_html
from app.services.reports.decisions_html_renderer import render_decisions_html

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/policy-changes")
def policy_changes_report(
    *,
    tenant_id: int = Query(..., ge=1),
    preset: str = Query("last24h"),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    tz: str = Query("Asia/Kolkata"),
    format: str = Query("html"),
    db: Session = Depends(get_db),
    api_key=Depends(get_api_key),
):
    # Compute time window
    try:
        f_utc, t_utc = compute_range(preset, from_iso=from_, to_iso=to, tz=tz)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Enumerate events
    events = list_policy_change_events(db, tenant_id=tenant_id, from_utc=f_utc, to_utc=t_utc, tz=tz)

    # HTML needs no-change section; others do not
    range_meta = {"preset": preset, "from_utc": fmt_rfc3339_utc(f_utc), "to_utc": fmt_rfc3339_utc(t_utc)}

    fmt = (format or "html").lower()

    # Build a filesystem-safe filename (avoid characters like ':' on Windows)
    raw_base = f"policy-changes_t{tenant_id}_from{range_meta['from_utc']}_to{range_meta['to_utc']}_{fmt}"
    safe_base = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_base)

    # Ensure reports directory exists under current working directory (project root in local runs)
    reports_dir = Path(os.getcwd()) / "reports"
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Do not fail the request if the directory cannot be created
        pass

    if fmt == "csv":
        body = pol_to_csv(events)  # bytes (includes UTF-8 BOM)
        # Save to disk
        try:
            (reports_dir / f"{safe_base}.csv").write_bytes(body)
        except Exception:
            pass
        headers = {"Content-Disposition": f"attachment; filename={safe_base}.csv"}
        return Response(content=body, media_type="text/csv; charset=utf-8", headers=headers)
    if fmt == "ndjson":
        body = pol_to_ndjson(events)  # bytes
        try:
            (reports_dir / f"{safe_base}.ndjson").write_bytes(body)
        except Exception:
            pass
        headers = {"Content-Disposition": f"attachment; filename={safe_base}.ndjson"}
        return Response(content=body, media_type="application/x-ndjson; charset=utf-8", headers=headers)
    if fmt == "json":
        body = pol_to_json(events)  # bytes
        try:
            (reports_dir / f"{safe_base}.json").write_bytes(body)
        except Exception:
            pass
        headers = {"Content-Disposition": f"attachment; filename={safe_base}.json"}
        return Response(content=body, media_type="application/json; charset=utf-8", headers=headers)

    # HTML (default)
    # Determine policies with no change in the last N days (cap)
    # For MVP, we cannot efficiently compute "all policies" here without a policy repo call; return empty recent list.
    html_doc = render_policy_changes_html(
        tenant_id=tenant_id,
        tz=tz,
        range_meta=range_meta,
        events=events,
        no_change_policies_recent=[],
        older_no_change_count=0,
    )
    # Save HTML to disk
    try:
        (reports_dir / f"{safe_base}.html").write_text(html_doc, encoding="utf-8")
    except Exception:
        pass
    headers = {"Content-Disposition": f"attachment; filename={safe_base}.html"}
    return Response(content=html_doc, media_type="text/html; charset=utf-8", headers=headers)


@router.get("/decisions")
def decisions_report(
    *,
    tenant_id: int = Query(..., ge=1),
    preset: str = Query("last24h"),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    tz: str = Query("Asia/Kolkata"),
    format: str = Query("html"),
    db: Session = Depends(get_db),
    api_key=Depends(get_api_key),
):
    # Compute time window
    try:
        f_utc, t_utc = compute_range(preset, from_iso=from_, to_iso=to, tz=tz)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Enumerate events
    events = list_decision_events(db, tenant_id=tenant_id, from_utc=f_utc, to_utc=t_utc, tz=tz)

    range_meta = {"preset": preset, "from_utc": fmt_rfc3339_utc(f_utc), "to_utc": fmt_rfc3339_utc(t_utc)}
    fmt = (format or "html").lower()

    # Build safe filename
    raw_base = f"decisions_t{tenant_id}_from{range_meta['from_utc']}_to{range_meta['to_utc']}_{fmt}"
    safe_base = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_base)

    reports_dir = Path(os.getcwd()) / "reports"
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    if fmt == "csv":
        body = dec_to_csv(events)
        try:
            (reports_dir / f"{safe_base}.csv").write_bytes(body)
        except Exception:
            pass
        headers = {"Content-Disposition": f"attachment; filename={safe_base}.csv"}
        return Response(content=body, media_type="text/csv; charset=utf-8", headers=headers)
    if fmt == "ndjson":
        body = dec_to_ndjson(events)
        try:
            (reports_dir / f"{safe_base}.ndjson").write_bytes(body)
        except Exception:
            pass
        headers = {"Content-Disposition": f"attachment; filename={safe_base}.ndjson"}
        return Response(content=body, media_type="application/x-ndjson; charset=utf-8", headers=headers)
    if fmt == "json":
        body = dec_to_json(events)
        try:
            (reports_dir / f"{safe_base}.json").write_bytes(body)
        except Exception:
            pass
        headers = {"Content-Disposition": f"attachment; filename={safe_base}.json"}
        return Response(content=body, media_type="application/json; charset=utf-8", headers=headers)

    # HTML rendering with stacked charts and table
    html_doc = render_decisions_html(
        tenant_id=tenant_id,
        tz=tz,
        range_meta=range_meta,
        events=events,
    )
    try:
        (reports_dir / f"{safe_base}.html").write_text(html_doc, encoding="utf-8")
    except Exception:
        pass
    headers = {"Content-Disposition": f"attachment; filename={safe_base}.html"}
    return Response(content=html_doc, media_type="text/html; charset=utf-8", headers=headers)
