
import asyncio
import sys
import os

# Ensure backend can be imported
sys.path.append(os.getcwd())

from sqlalchemy import text
from backend.database import engine

async def main():
    """
    Adds the 'idx_user_created_at' index to the conversations table concurrently.
    This is a manual migration script to optimize the list_conversations query.
    """
    if not engine:
        print("No database configured.")
        return

    print("Connecting to database...")
    # Use execution_options on engine to set isolation level for concurrent index creation
    engine_autocommit = engine.execution_options(isolation_level="AUTOCOMMIT")

    async with engine_autocommit.connect() as conn:
        print("Creating index 'idx_user_created_at' concurrently...")
        try:
            # We use IF NOT EXISTS to be safe
            await conn.execute(text(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_created_at ON conversations (user_id, created_at)"
            ))
            print("Index created successfully (or already existed).")
        except Exception as e:
            # Check if it's just "relation already exists" which might not be caught by IF NOT EXISTS on some old postgres?
            # But IF NOT EXISTS is standard.
            import traceback
            traceback.print_exc()
            print(f"Failed to create index: {e}")

if __name__ == "__main__":
    asyncio.run(main())
