"""Quick script to verify policy exists in database."""
from app.db.session import SessionLocal
from app.repos.policy_repo import SqlAlchemyPolicyRepo

db = SessionLocal()
repo = SqlAlchemyPolicyRepo(db)

try:
    policy = repo.get_policy_by_id(1)
    print(f"✓ Policy found: id={policy.id}, name={policy.name}, slug={policy.slug}")
    
    versions = repo.list_versions(1)
    print(f"✓ Versions: {len(versions)} total")
    for v in versions:
        print(f"  - Version {v.version} (id={v.id})")
        if v.document and 'regulatory_frameworks' in v.document:
            print(f"    Frameworks: {v.document['regulatory_frameworks']}")
except Exception as e:
    print(f"✗ Error: {e}")
finally:
    db.close()
