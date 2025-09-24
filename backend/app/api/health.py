from fastapi import APIRouter, HTTPException
from app.services.llm_factory import llm_service
from app.config import settings
import httpx
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "llm_provider": settings.llm_provider,
        "ollama_url": settings.ollama_base_url if settings.llm_provider == "ollama" else None,
        "ollama_model": settings.ollama_model if settings.llm_provider == "ollama" else None
    }


@router.get("/health/llm")
async def llm_health_check():
    """Check if LLM service is available"""
    try:
        if settings.llm_provider == "ollama":
            # Test Ollama connection
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
                if response.status_code != 200:
                    raise HTTPException(status_code=503, detail="Ollama service unavailable")
            
            # Test simple completion
            test_messages = [{"role": "user", "content": "Hello, respond with just 'OK'"}]
            response_chunks = []
            async for chunk in llm_service.generate_chat_completion(test_messages, stream=False):
                response_chunks.append(chunk)
                break  # Just test if it works
                
        return {
            "status": "healthy",
            "provider": settings.llm_provider,
            "model": settings.ollama_model if settings.llm_provider == "ollama" else settings.azure_openai_deployment_name,
            "test_response": "LLM is responding correctly"
        }
    except Exception as e:
        logger.error(f"LLM health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {str(e)}")


@router.get("/health/embedding")
async def embedding_health_check():
    """Check if embedding service is available"""
    try:
        # Test simple embedding
        test_embedding = await llm_service.generate_embedding("test")
        
        return {
            "status": "healthy",
            "provider": settings.llm_provider,
            "embedding_model": settings.ollama_embedding_model if settings.llm_provider == "ollama" else settings.azure_openai_embedding_deployment_name,
            "embedding_dimension": len(test_embedding),
            "test_response": "Embedding service is working correctly"
        }
    except Exception as e:
        logger.error(f"Embedding health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {str(e)}")
