import asyncio
import sys
import os
import httpx

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.langchain import langchain_ollama_service
from app.config import settings


async def test_ollama_chat():
    """Test Ollama Chat Completion"""
    print("🤖 Testing Ollama Chat Completion...")
    
    messages = [
        {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
        {"role": "user", "content": "Erkläre mir in 2 Sätzen was Künstliche Intelligenz ist."}
    ]
    
    try:
        print("💬 Streaming Response:")
        async for chunk in langchain_ollama_service.generate_chat_completion(messages, stream=True):
            print(chunk, end='', flush=True)
        print("\n")
        
        print("📝 Non-streaming Response:")
        async for response in langchain_ollama_service.generate_chat_completion(messages, stream=False):
            print(response)
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_ollama_embeddings():
    """Test Ollama Embeddings"""
    print("\n🔢 Testing Ollama Embeddings...")
    
    try:
        # Single embedding
        text = "Das ist ein Test für Embeddings."
        embedding = await langchain_ollama_service.generate_embedding(text)
        print(f"✅ Single embedding dimension: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
        
        # Batch embeddings
        texts = [
            "Erster Text für Batch-Embeddings",
            "Zweiter Text für Batch-Embeddings",
            "Dritter Text für Batch-Embeddings"
        ]
        embeddings = await langchain_ollama_service.generate_embeddings_batch(texts)
        print(f"✅ Batch embeddings count: {len(embeddings)}")
        print(f"Each embedding dimension: {len(embeddings[0])}")
        
    except Exception as e:
        print(f"❌ Embedding Error: {e}")


async def test_token_counting():
    """Test Token Counting"""
    print("\n🔢 Testing Token Counting...")
    
    text = "Das ist ein Test-Text für die Token-Zählung mit mehreren Wörtern."
    token_count = langchain_ollama_service.count_tokens(text)
    print(f"✅ Text: '{text}'")
    print(f"✅ Estimated tokens: {token_count}")


async def test_docker_setup():
    """Test Docker Setup"""
    print("\n🐳 Testing Docker Setup...")
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test Health
            response = await client.get(f"{base_url}/api/v1/health")
            print(f"✅ Health: {response.json()}")
            
            # Test LLM Health
            response = await client.get(f"{base_url}/api/v1/health/llm")
            print(f"✅ LLM Health: {response.json()}")
            
            # Test Embedding Health
            response = await client.get(f"{base_url}/api/v1/health/embedding")
            print(f"✅ Embedding Health: {response.json()}")
            
        except Exception as e:
            print(f"❌ Docker Error: {e}")
            print("Make sure docker services are running:")
            print("  docker-compose -f docker-compose.ollama.yml up -d")


async def test_ollama_direct():
    """Test Ollama directly"""
    print("\n🔗 Testing Ollama Direct Connection...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Test Ollama API
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            if response.status_code == 200:
                models = response.json()
                print(f"✅ Ollama is running with models: {[m['name'] for m in models.get('models', [])]}")
            else:
                print(f"❌ Ollama API returned status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Ollama Connection Error: {e}")
            print(f"Make sure Ollama is running at: {settings.ollama_base_url}")


async def main():
    print("🚀 Starting Ollama LangChain Tests...")
    print("=" * 50)
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"Ollama URL: {settings.ollama_base_url}")
    print(f"Ollama Model: {settings.ollama_model}")
    print(f"Ollama Embedding Model: {settings.ollama_embedding_model}")
    print("=" * 50)
    
    # Test different scenarios
    await test_ollama_direct()
    
    if settings.llm_provider == "ollama":
        await test_token_counting()
        await test_ollama_chat()
        await test_ollama_embeddings()
    
    await test_docker_setup()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\n🔧 Setup Instructions:")
    print("1. Start Ollama:")
    print("   docker-compose -f docker-compose.ollama.yml up -d")
    print("2. Check logs:")
    print("   docker-compose -f docker-compose.ollama.yml logs -f")
    print("3. Test API:")
    print("   curl http://localhost:8000/api/v1/health/llm")


if __name__ == "__main__":
    asyncio.run(main())
