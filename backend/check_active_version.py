"""Check which policy version is active."""
from app.db.session import SessionLocal
from app.repos.policy_repo import SqlAlchemyPolicyRepo

db = SessionLocal()
repo = SqlAlchemyPolicyRepo(db)

policy = repo.get_policy_by_id(1)
print(f"Policy: {policy.name} (id={policy.id})")

versions = repo.list_versions(1)
print(f"\nAll versions:")
for v in versions:
    active_marker = " ← ACTIVE" if v.is_active else ""
    blocked_terms = v.document.get('blocked_terms', []) if v.document else []
    print(f"  Version {v.version} (id={v.id}): is_active={v.is_active}{active_marker}")
    print(f"    Blocked terms: {blocked_terms[:5]}{'...' if len(blocked_terms) > 5 else ''}")

active_version = repo.get_active_version(1)
if active_version:
    print(f"\nActive version from get_active_version(): {active_version.version} (id={active_version.id})")
    blocked_terms = active_version.document.get('blocked_terms', [])
    print(f"  Blocked terms: {blocked_terms}")
else:
    print("\nNo active version found!")

db.close()
