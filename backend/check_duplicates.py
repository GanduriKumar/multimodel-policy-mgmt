"""Check for duplicate decision logs with the same input."""
from app.db.session import SessionLocal
from app.models.decision_log import DecisionLog
from app.models.request_log import RequestLog
from sqlalchemy import select, func

db = SessionLocal()

# Get the most recent decision logs with their request texts
stmt = (
    select(
        DecisionLog.id.label('decision_id'),
        RequestLog.input_text,
        RequestLog.input_hash,
        DecisionLog.allowed,
        DecisionLog.risk_score,
        DecisionLog.created_at
    )
    .join(RequestLog, DecisionLog.request_log_id == RequestLog.id)
    .where(DecisionLog.tenant_id == 1)
    .order_by(DecisionLog.created_at.desc())
    .limit(20)
)

results = db.execute(stmt).all()

print(f"\n{'='*80}")
print("Last 20 Decision Logs:")
print(f"{'='*80}\n")

for row in results:
    text_preview = row.input_text[:60] + "..." if len(row.input_text) > 60 else row.input_text
    print(f"Decision ID: {row.decision_id}")
    print(f"  Text: {text_preview}")
    print(f"  Hash: {row.input_hash}")
    print(f"  Allowed: {row.allowed}, Risk: {row.risk_score}")
    print(f"  Time: {row.created_at}")
    print()

# Check for exact duplicates (same hash, close timestamps)
print(f"{'='*80}")
print("Checking for potential duplicates (same hash within 1 second):")
print(f"{'='*80}\n")

duplicates = db.execute(
    select(RequestLog.input_hash, func.count(DecisionLog.id).label('count'))
    .join(RequestLog, DecisionLog.request_log_id == RequestLog.id)
    .where(DecisionLog.tenant_id == 1)
    .group_by(RequestLog.input_hash)
    .having(func.count(DecisionLog.id) > 1)
).all()

if duplicates:
    for dup in duplicates:
        print(f"Hash {dup.input_hash}: {dup.count} decisions")
else:
    print("No exact hash duplicates found.")

db.close()
