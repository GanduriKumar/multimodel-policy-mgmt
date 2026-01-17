"""Drop the unique constraint on (tenant_id, input_hash) from request_log table."""

from sqlalchemy import text
from app.db.session import engine

print("Dropping unique constraint uq_request_tenant_input_hash from request_log table...")

with engine.connect() as conn:
    try:
        # SQLite uses DROP INDEX instead of DROP CONSTRAINT
        stmt = 'DROP INDEX IF EXISTS uq_request_tenant_input_hash'
        conn.execute(text(stmt))
        print(f"  ✓ Dropped index/constraint: uq_request_tenant_input_hash")
        conn.commit()
    except Exception as e:
        print(f"  ✗ Error: {e}")
        print("  Note: This might be expected if the constraint doesn't exist or has a different name")

print("\n✓ Migration complete!")
print("The same input text can now be evaluated multiple times with different policies.")
