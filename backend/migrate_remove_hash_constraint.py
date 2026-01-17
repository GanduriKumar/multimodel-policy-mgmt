"""Migrate request_log table to remove unique constraint on (tenant_id, input_hash)."""

from sqlalchemy import text
from app.db.session import engine

print("Migrating request_log table to allow duplicate input_hash values...")

with engine.connect() as conn:
    try:
        # Step 1: Create new table without the unique constraint
        print("  Creating request_log_new table...")
        conn.execute(text("""
            CREATE TABLE request_log_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                policy_id INTEGER,
                policy_version_id INTEGER,
                request_id VARCHAR,
                input_text TEXT NOT NULL,
                input_hash VARCHAR(64),
                user_agent VARCHAR,
                client_ip VARCHAR,
                metadata JSON,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenant (id) ON DELETE CASCADE,
                FOREIGN KEY(policy_id) REFERENCES policy (id) ON DELETE SET NULL,
                FOREIGN KEY(policy_version_id) REFERENCES policy_version (id) ON DELETE SET NULL,
                CONSTRAINT uq_request_tenant_request_id UNIQUE (tenant_id, request_id)
            )
        """))
        
        # Step 2: Copy data from old table to new table
        print("  Copying data from request_log to request_log_new...")
        conn.execute(text("""
            INSERT INTO request_log_new 
            SELECT id, tenant_id, policy_id, policy_version_id, request_id, input_text, 
                   input_hash, user_agent, client_ip, metadata, created_at, updated_at
            FROM request_log
        """))
        
        # Step 3: Drop old table
        print("  Dropping old request_log table...")
        conn.execute(text("DROP TABLE request_log"))
        
        # Step 4: Rename new table to original name
        print("  Renaming request_log_new to request_log...")
        conn.execute(text("ALTER TABLE request_log_new RENAME TO request_log"))
        
        # Step 5: Recreate indexes
        print("  Recreating indexes...")
        conn.execute(text("CREATE INDEX ix_request_tenant_created ON request_log (tenant_id, created_at)"))
        conn.execute(text("CREATE INDEX ix_request_log_input_hash ON request_log (input_hash)"))
        
        conn.commit()
        print("\n✓ Migration complete!")
        print("The same input text can now be evaluated multiple times.")
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
