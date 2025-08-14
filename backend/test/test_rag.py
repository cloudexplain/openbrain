import asyncio
from app.models.database import AsyncSessionLocal
from app.services.embedding_service import embedding_service

async def test_similarity_search():
    async with AsyncSessionLocal() as db:
        # Test similarity search
        results = await embedding_service.similarity_search(
            db=db,
            query='test query',
            limit=5,
            similarity_threshold=0.7
        )
        print(f'Found {len(results)} results')
        for r in results:
            print(f'- Content preview: {r.content[:100]}...')
            
if __name__ == "__main__":
    asyncio.run(test_similarity_search())