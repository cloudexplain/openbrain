import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import AsyncSessionLocal
from app.services.embedding_service import embedding_service
from sqlalchemy import text

async def test_similarity_search_debug():
    async with AsyncSessionLocal() as db:
        # First, check if we have any documents and chunks
        result = await db.execute(text("SELECT COUNT(*) as count FROM documents"))
        doc_count = result.scalar()
        print(f"Total documents in DB: {doc_count}")
        
        result = await db.execute(text("SELECT COUNT(*) as count FROM document_chunks"))
        chunk_count = result.scalar()
        print(f"Total chunks in DB: {chunk_count}")
        
        if chunk_count > 0:
            # Get a sample chunk to see the content
            result = await db.execute(text("SELECT content, chunk_metadata FROM document_chunks LIMIT 3"))
            rows = result.fetchall()
            print("\nSample chunks in DB:")
            for row in rows:
                print(f"  Content: {row.content[:100]}...")
                print(f"  Metadata: {row.chunk_metadata}")
                print()
        
        # Test different queries
        test_queries = [
            "What is my name?",
            "When was I born?",
            "Peter",
            "October 31st",
            "1991",
            "birthday"
        ]
        
        for query in test_queries:
            print(f"\nTesting query: '{query}'")
            try:
                results = await embedding_service.similarity_search(
                    db=db,
                    query=query,
                    limit=3,
                    similarity_threshold=0.5  # Lower threshold for testing
                )
                print(f"  Found {len(results)} results")
                for i, r in enumerate(results, 1):
                    print(f"  Result {i}:")
                    print(f"    Distance: {getattr(r, 'search_distance', 'N/A')}")
                    print(f"    Content: {r.content[:150]}...")
            except Exception as e:
                print(f"  Error: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_similarity_search_debug())