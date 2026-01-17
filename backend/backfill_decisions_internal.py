"""
Backfill missing DecisionLog entries without relying on the HTTP server.
Uses the DecisionService directly to evaluate and persist decisions for each request
that lacks a DecisionLog.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.db.session import engine, SessionLocal
from app.repos.policy_repo import SqlAlchemyPolicyRepo
from app.repos.evidence_repo import SqlAlchemyEvidenceRepo
from app.repos.audit_repo import SqlAlchemyAuditRepo
from app.core.deps import DecisionService


def main(limit: int = 50) -> int:
    with engine.connect() as conn:
        rows = conn.execute(text(
            """
            SELECT id, tenant_id, policy_id, input_text
            FROM request_log r
            WHERE NOT EXISTS (
              SELECT 1 FROM decision_log d WHERE d.request_log_id = r.id
            )
            ORDER BY r.created_at DESC
            LIMIT :limit
            """
        ), {"limit": limit}).fetchall()
    if not rows:
        print("No requests missing decisions.")
        return 0

    ok = 0
    failed = 0
    for rid, tenant_id, policy_id, input_text in rows:
        db = SessionLocal()
        try:
            pol_repo = SqlAlchemyPolicyRepo(db)
            ev_repo = SqlAlchemyEvidenceRepo(db)
            audit_repo = SqlAlchemyAuditRepo(db)
            service = DecisionService(policy_repo=pol_repo, evidence_repo=ev_repo, audit_repo=audit_repo)
            # Fallback to policy_id=1 if missing
            pid = int(policy_id) if policy_id is not None else 1
            res: Any = service.protect(
                tenant_id=int(tenant_id),
                input_text=input_text,
                policy_id=pid,
                metadata={"stage": "backfill"},
            )
            allowed = bool(getattr(res, "allowed", False)) if not isinstance(res, dict) else bool(res.get("allowed", False))
            ok += 1
            print(f"  ✓ Backfilled decision for request {rid}: allowed={allowed}")
        except Exception as e:
            failed += 1
            print(f"  ✗ Backfill failed for request {rid}: {e}")
        finally:
            db.close()

    print(f"Done. Success: {ok}, Failed: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
