import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import AsyncSessionLocal
from app.services.embedding_service import embedding_service
from sqlalchemy import text
import numpy as np

async def verify_embeddings():
    async with AsyncSessionLocal() as db:
        # Test embedding generation
        test_text = "My name is Peter and I was born on October 31st, 1991"
        print(f"Test text: {test_text}")
        
        # Generate embedding
        embedding = embedding_service.embed_text(test_text)
        print(f"Embedding dimensions: {len(embedding)}")
        print(f"Embedding type: {type(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
        
        # Test another query
        query = "What is my name?"
        query_embedding = embedding_service.embed_text(query)
        
        # Calculate cosine similarity manually
        def cosine_similarity(a, b):
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            return dot_product / (norm_a * norm_b)
        
        similarity = cosine_similarity(embedding, query_embedding)
        print(f"\nManual cosine similarity between test text and query: {similarity}")
        
        # Now test the actual database query
        print("\n--- Testing direct SQL query ---")
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Test the raw SQL query
        query_sql = """
            SELECT dc.id, dc.content, 
                   (dc.embedding <=> :query_embedding::vector) as distance
            FROM document_chunks dc
            ORDER BY dc.embedding <=> :query_embedding::vector
            LIMIT 5
        """
        
        try:
            result = await db.execute(text(query_sql), {'query_embedding': embedding_str})
            rows = result.fetchall()
            print(f"Found {len(rows)} results from direct SQL")
            for row in rows:
                print(f"  Distance: {row.distance:.4f}, Content: {row.content[:100]}...")
        except Exception as e:
            print(f"SQL Error: {e}")
            
        # Also check if embeddings are stored correctly
        print("\n--- Checking stored embeddings ---")
        check_sql = """
            SELECT dc.id, dc.content, 
                   octet_length(dc.embedding::text) as embedding_size
            FROM document_chunks dc
            LIMIT 3
        """
        result = await db.execute(text(check_sql))
        rows = result.fetchall()
        for row in rows:
            print(f"  ID: {row.id}, Embedding size: {row.embedding_size}, Content: {row.content[:50]}...")

if __name__ == "__main__":
    asyncio.run(verify_embeddings())