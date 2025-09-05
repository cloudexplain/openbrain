import logging
import os
from app.config import settings

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("LLM provider -> %r", settings.llm_provider)
logger.info("Ollama base url -> %r", settings.ollama_base_url)

# Expose llm_service (may be None)
llm_service = None

provider = (settings.llm_provider or "azure_openai").lower()
logger.info("LLM provider setting: %s", provider)

if provider == "ollama":
    try:
        from app.services.langchain import langchain_ollama_service as llm_service  # type: ignore
        logger.info("Using Ollama LLM service (base_url=%s, model=%s)", settings.ollama_base_url, settings.ollama_model)
    except Exception as e:
        logger.exception("Failed to initialize Ollama service: %s", e)
        llm_service = None
elif provider in ("azure", "azure_openai", "azure-openai"):
    try:
        from app.services.azure_openai import AzureOpenAIService
        llm_service = AzureOpenAIService(
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment_name=settings.azure_openai_deployment_name,
            api_version=settings.azure_openai_api_version,
        )
        logger.info("Using Azure OpenAI service (deployment=%s)", settings.azure_openai_deployment_name)
    except Exception as e:
        logger.exception("Failed to initialize AzureOpenAI service: %s", e)
        llm_service = None
else:
    logger.warning("Unknown LLM provider '%s', falling back to Azure OpenAI", provider)
    try:
        from app.services.azure_openai import AzureOpenAIService
        llm_service = AzureOpenAIService(
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment_name=settings.azure_openai_deployment_name,
            api_version=settings.azure_openai_api_version,
        )
    except Exception as e:
        logger.exception("Fallback Azure init failed: %s", e)
        llm_service = None