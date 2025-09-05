from app.config import settings
from app.services.azure_openai import azure_openai_service
from app.services.langchain import langchain_ollama_service
import logging

logger = logging.getLogger(__name__)


def get_llm_service():
    """Factory function um den konfigurierten LLM Service zu bekommen"""
    provider = settings.llm_provider.lower()
    
    logger.info(f"Initializing LLM service with provider: {provider}")
    
    if provider == "ollama":
        logger.info(f"Using Ollama at {settings.ollama_base_url} with model {settings.ollama_model}")
        return langchain_ollama_service
    elif provider == "azure_openai":
        logger.info(f"Using Azure OpenAI with deployment {settings.azure_openai_deployment_name}")
        return azure_openai_service
    else:
        logger.warning(f"Unknown LLM provider '{provider}', falling back to Azure OpenAI")
        return azure_openai_service


# Global service instance
llm_service = get_llm_service()
