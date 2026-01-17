from sqlalchemy import text
from app.db.session import engine

print("Checking recent requests and decision presence...")
with engine.connect() as conn:
    # Fetch last 50 requests
    reqs = conn.execute(text("SELECT id, tenant_id, created_at FROM request_log ORDER BY created_at DESC LIMIT 50")).fetchall()
    missing = []
    for r in reqs:
        did = conn.execute(text("SELECT id, allowed FROM decision_log WHERE request_log_id = :rid LIMIT 1"), {"rid": r[0]}).fetchone()
        missing.append((r[0], did is None))
    total = len(missing)
    none_count = sum(1 for _, m in missing if m)
    print(f"Recent requests: {total}, without decision: {none_count}")
    if none_count:
        print("IDs missing decisions:")
        print([rid for rid, m in missing if m])
    else:
        print("All recent requests have a decision.")
