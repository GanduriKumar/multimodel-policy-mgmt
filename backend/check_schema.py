"""Check the current schema of request_log table."""
from app.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT sql FROM sqlite_master WHERE name='request_log'"))
    row = result.fetchone()
    if row:
        print("Current request_log schema:")
        print(row[0])
    else:
        print("Table not found!")
