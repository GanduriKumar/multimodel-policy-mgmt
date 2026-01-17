"""
Backfill DecisionLog entries for existing RequestLog rows (without creating new requests).
Evaluates the active policy and risk, then logs a decision tied to each specific request.
"""
from __future__ import annotations

from typing import Any, Optional, Set

from sqlalchemy import text

from app.db.session import engine, SessionLocal
from app.repos.policy_repo import SqlAlchemyPolicyRepo
from app.repos.evidence_repo import SqlAlchemyEvidenceRepo
from app.repos.audit_repo import SqlAlchemyAuditRepo
from app.schemas.policy_format import PolicyDoc
from app.services.policy_engine import evaluate_policy
from app.services.risk_engine import compute_risk
from app.core.patterns import detect_pii_like


def load_active_policy_doc(policy_repo: SqlAlchemyPolicyRepo, tenant_id: int, policy_id: Optional[int]) -> tuple[PolicyDoc, Optional[int], Optional[int]]:
    doc: Optional[dict] = None
    pol = None
    if policy_id:
        try:
            pol = policy_repo.get_policy_by_id(int(policy_id))
        except Exception:
            pol = None
    if pol is not None:
        try:
            pv = policy_repo.get_active_version(pol.id)
            doc = getattr(pv, "document", None)
            pv_id = getattr(pv, "id", None)
        except Exception:
            pv_id = None
    else:
        pv_id = None
    if not isinstance(doc, dict):
        policy_doc = PolicyDoc(
            blocked_terms=[], allowed_sources=[], required_evidence_types={}, pii_rules={}, risk_threshold=100
        )
    else:
        policy_doc = PolicyDoc(**doc)
    pol_id = getattr(pol, "id", None) if pol is not None else None
    return policy_doc, pol_id, pv_id


def evaluate_and_log_for_request(rid: int, tenant_id: int, input_text: str, policy_id: Optional[int]) -> bool:
    db = SessionLocal()
    try:
        pol_repo = SqlAlchemyPolicyRepo(db)
        audit_repo = SqlAlchemyAuditRepo(db)
        # Load active policy doc
        policy_doc, pol_id, pv_id = load_active_policy_doc(pol_repo, tenant_id, policy_id or 1)
        # Evaluate policy
        ev_types: Set[str] = set()
        policy_allowed, policy_reasons = evaluate_policy(policy_doc, input_text, ev_types)
        # PII enforcement
        pii_blocked = False
        pii_reasons = []
        if policy_doc.pii_rules:
            pii_markers = detect_pii_like(input_text)
            for marker in pii_markers or []:
                pii_type = marker.replace("_like", "").replace("_", "")
                for rule_key, rule_config in policy_doc.pii_rules.items():
                    if rule_key.lower() in pii_type.lower() or pii_type.lower() in rule_key.lower():
                        if isinstance(rule_config, dict):
                            action = rule_config.get('action', 'detect'); enabled = rule_config.get('enabled', True)
                        else:
                            action = 'detect'; enabled = True
                        if enabled:
                            if action == 'block': pii_blocked = True; pii_reasons.append(f"pii_blocked:{pii_type}")
                            elif action in ['mask','redact']: pii_reasons.append(f"pii_{action}:{pii_type}")
                            else: pii_reasons.append(f"pii_detected:{pii_type}")
        if pii_blocked:
            policy_allowed = False
            policy_reasons.extend(pii_reasons)
        # Risk
        risk_score, risk_reasons = compute_risk(input_text, evidence_present=False)
        allowed = policy_allowed
        reasons = list(policy_reasons) + list(risk_reasons)
        if risk_score >= int(policy_doc.risk_threshold):
            allowed = False
            reasons.append(f"risk_above_threshold:{risk_score}>={policy_doc.risk_threshold}")
        # Log decision tied to existing request
        audit_repo.log_decision(
            tenant_id=tenant_id,
            request_log_id=rid,
            allowed=allowed,
            reasons=reasons,
            policy_id=pol_id,
            policy_version_id=pv_id,
            risk_score=risk_score,
            policy_version_snapshot=policy_doc.model_dump() if hasattr(policy_doc, 'model_dump') else None,
        )
        return True
    finally:
        db.close()


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
    print(f"Backfilling {len(rows)} request(s) with decisions (without creating new requests)...")
    ok = 0
    failed = 0
    for rid, tenant_id, policy_id, input_text in rows:
        try:
            if evaluate_and_log_for_request(int(rid), int(tenant_id), input_text, int(policy_id) if policy_id is not None else None):
                ok += 1
                print(f"  ✓ Backfilled decision for request {rid}")
            else:
                failed += 1
                print(f"  ✗ Failed to backfill request {rid}")
        except Exception as e:
            failed += 1
            print(f"  ✗ Error for request {rid}: {e}")
    print(f"Done. Success: {ok}, Failed: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
