"""Add enhanced compliance audit columns to decision_log table."""

from sqlalchemy import text
from app.db.session import engine

print("Adding enhanced compliance columns to decision_log table...")

columns_to_add = [
    ('reasoning_chain', 'JSON'),
    ('compliance_frameworks', 'JSON'),
    ('regulatory_mappings', 'JSON'),
    ('engine_scores', 'JSON'),
    ('policy_version_snapshot', 'JSON'),
]

with engine.connect() as conn:
    for column_name, column_type in columns_to_add:
        try:
            stmt = f'ALTER TABLE decision_log ADD COLUMN {column_name} {column_type}'
            conn.execute(text(stmt))
            print(f"  ✓ Added column: {column_name}")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print(f"  - Column {column_name} already exists (skipped)")
            else:
                print(f"  ✗ Error adding {column_name}: {e}")
    
    conn.commit()

print("\n✓ Migration complete!")
print("You can now restart your backend server.")
