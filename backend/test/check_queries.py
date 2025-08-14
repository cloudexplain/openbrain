import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.models.database import AsyncSessionLocal

async def check_recent_queries():
    async with AsyncSessionLocal() as db:
        # Check if pg_stat_statements is enabled
        check_extension = await db.execute(text("""
            SELECT extname FROM pg_extension WHERE extname = 'pg_stat_statements';
        """))
        if not check_extension.fetchone():
            print("pg_stat_statements is not enabled. You may need to restart PostgreSQL.")
            return
        
        # Get recent queries
        result = await db.execute(text("""
            SELECT 
                substring(query, 1, 200) as query_snippet,
                calls,
                round(total_exec_time::numeric, 2) as total_ms,
                round(mean_exec_time::numeric, 2) as mean_ms
            FROM pg_stat_statements
            WHERE query LIKE '%embedding%' OR query LIKE '%vector%'
            ORDER BY max_exec_time DESC
            LIMIT 10;
        """))
        
        rows = result.fetchall()
        if rows:
            print("Recent vector/embedding queries:")
            print("-" * 80)
            for row in rows:
                print(f"Query: {row.query_snippet}...")
                print(f"Calls: {row.calls}, Total: {row.total_ms}ms, Mean: {row.mean_ms}ms")
                print("-" * 80)
        else:
            print("No vector/embedding queries found in pg_stat_statements")
            
        # Also check the last 5 queries overall
        result = await db.execute(text("""
            SELECT 
                substring(query, 1, 200) as query_snippet,
                calls
            FROM pg_stat_statements
            WHERE query NOT LIKE '%pg_stat_statements%'
            ORDER BY max_exec_time DESC
            LIMIT 5;
        """))
        
        rows = result.fetchall()
        if rows:
            print("\nLast 5 queries (any type):")
            print("-" * 80)
            for row in rows:
                print(f"Query: {row.query_snippet}...")
                print(f"Calls: {row.calls}")
                print("-" * 80)

if __name__ == "__main__":
    asyncio.run(check_recent_queries())