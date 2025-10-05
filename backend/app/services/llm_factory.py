import logging
import os
import httpx
from typing import Optional, Any
from app.config import settings

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("LLM provider -> %r", settings.llm_provider)
logger.info("Ollama base url -> %r", settings.ollama_base_url)

# Expose llm_service (may be None)
llm_service: Optional[Any] = None

provider = (settings.llm_provider or "azure_openai").lower()
logger.info("LLM provider setting: %s", provider)


# --- helper: check if ollama base_url is reachable ---
def _check_ollama_reachable(base_url: str, timeout: float = 2.0) -> bool:
    """
    Versucht mehrere bekannte Ollama-Endpunkte (priorisiert /v1/models).
    Gibt True zurück, wenn ein Endpunkt HTTP 200 liefert. Loggt den erfolgreichen Endpunkt.
    """
    endpoints = ["/v1/models", "/models", "/api/models", "/health", "/"]
    for ep in endpoints:
        url = base_url.rstrip("/") + ep
        try:
            logger.debug("Checking Ollama endpoint %s", url)
            resp = httpx.get(url, timeout=timeout)
            logger.info("Ollama check %s -> %s", url, resp.status_code)
            if resp.status_code == 200:
                try:
                    logger.debug("Ollama response preview (%s): %s", url, resp.text[:400])
                except Exception:
                    pass
                logger.info("Ollama reachable via %s", url)
                return True
        except Exception as e:
            logger.debug("Request to %s failed: %s", url, e)
    logger.warning("None of the Ollama endpoints returned 200 (base_url=%s)", base_url)
    return False


if provider == "ollama":
    try:
        # import the configured ollama/langchain helper (should expose a call interface)
        from app.services.langchain import langchain_ollama_service as llm_service  # type: ignore
        logger.info(
            "Using Ollama LLM service (base_url=%s, model=%s)",
            settings.ollama_base_url,
            settings.ollama_model,
        )

        # runtime diagnostics
        try:
            logger.debug("llm_service type=%s", type(llm_service))
            logger.debug(
                "llm_service dir (first 100): %s",
                [a for a in dir(llm_service) if not a.startswith("_")][:100],
            )
        except Exception:
            logger.exception("Failed to introspect llm_service object")

        # check network reachability to ollama (tries /v1/models first)
        if not _check_ollama_reachable(settings.ollama_base_url):
            logger.warning(
                "Ollama does not appear reachable at %s — requests to LLM will fail",
                settings.ollama_base_url,
            )
    except Exception as e:
        logger.exception("Failed to initialize Ollama service: %s", e)
        llm_service = None

elif provider in ("azure", "azure_openai", "azure-openai"):
    try:
        from app.services.azure_openai import AzureOpenAIService

        llm_service = AzureOpenAIService()
        logger.info(
            "Using Azure OpenAI service (deployment=%s)",
            settings.azure_openai_deployment_name,
        )
        try:
            logger.debug("llm_service type=%s", type(llm_service))
            logger.debug(
                "llm_service dir (first 100): %s",
                [a for a in dir(llm_service) if not a.startswith("_")][:100],
            )
        except Exception:
            logger.exception("Failed to introspect Azure llm_service")
    except Exception as e:
        logger.exception("Failed to initialize AzureOpenAI service: %s", e)
        llm_service = None

else:
    logger.warning("Unknown LLM provider '%s', falling back to Azure OpenAI", provider)
    try:
        from app.services.azure_openai import AzureOpenAIService

        llm_service = AzureOpenAIService()
    except Exception as e:
        logger.exception("Fallback Azure init failed: %s", e)
        llm_service = None


# --- runtime-access helpers ---
def get_llm_service() -> Optional[Any]:
    """Gibt das konfigurierte llm_service-Objekt (oder None) zurück."""
    try:
        logger.debug("get_llm_service -> %s", type(llm_service))
    except Exception:
        pass
    return llm_service


def require_llm_service() -> Any:
    """Wird von Endpunkten verwendet; wirft RuntimeError, wenn kein LLM-Service verfügbar."""
    svc = get_llm_service()
    if svc is None:
        target = settings.ollama_base_url if provider == "ollama" else "Azure"
        msg = (
            f"No LLM service initialized (provider={provider}). "
            f"Prüfe Logs und Verbindung zu {target}."
        )
        logger.error(msg)
        raise RuntimeError(msg)
    return svc
