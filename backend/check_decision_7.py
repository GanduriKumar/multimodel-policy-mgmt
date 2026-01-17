"""Check decision log ID 7 in detail."""
from app.db.session import SessionLocal
from app.models.decision_log import DecisionLog
from app.models.request_log import RequestLog
from sqlalchemy import select

db = SessionLocal()

# Get decision log 7
stmt = select(DecisionLog).where(DecisionLog.id == 7)
decision = db.execute(stmt).scalar_one_or_none()

if decision:
    print(f"Decision Log ID: {decision.id}")
    print(f"  Allowed: {decision.allowed}")
    print(f"  Reasons: {decision.reasons}")
    print(f"  Risk Score: {decision.risk_score}")
    print(f"  Policy ID: {decision.policy_id}")
    print(f"  Policy Version ID: {decision.policy_version_id}")
    print(f"  Created: {decision.created_at}")
    
    # Get the request
    stmt = select(RequestLog).where(RequestLog.id == decision.request_log_id)
    request = db.execute(stmt).scalar_one_or_none()
    
    if request:
        print(f"\nRequest Log ID: {request.id}")
        print(f"  Input Text: {request.input_text}")
        print(f"  Metadata: {request.metadata_json}")
else:
    print("Decision log 7 not found")

db.close()
