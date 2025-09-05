import os
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "smollm2:135m")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
_DEFAULT_TIMEOUT = 30.0

logger = logging.getLogger(__name__)


class LangchainOllamaService:
    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        embedding_model: str = OLLAMA_EMBEDDING_MODEL,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_model = embedding_model
        self._client = httpx.Client(timeout=_DEFAULT_TIMEOUT)

    def generate(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a generation request to Ollama.
        For streaming responses (multiple JSON lines) all 'response' parts are concatenated
        and returned in the 'response' field.
        """
        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {"model": self.model, "prompt": prompt}
        if params:
            payload.update(params)

        resp = self._client.post(url, json=payload)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            logger.error("Ollama generate returned status %s: %s", resp.status_code, resp.text)
            raise

        # try full JSON, otherwise parse line-by-line and concat 'response'
        try:
            return resp.json()
        except Exception:
            text = resp.text or ""
            parsed: List[Dict[str, Any]] = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        parsed.append(obj)
                except Exception:
                    continue

            if parsed:
                combined = "".join(o.get("response", "") for o in parsed if isinstance(o.get("response", ""), str))
                base = dict(parsed[-1])
                base["response"] = combined
                return base

            logger.warning("Ollama generate: could not parse JSON, returning raw text")
            return {"raw": text}

    def embed(self, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        last_exc: Optional[Exception] = None
        for model_choice in (self.embedding_model, self.model):
            payload = {"model": model_choice, "input": text}
            try:
                resp = self._client.post(url, json=payload)
                resp.raise_for_status()
                try:
                    data = resp.json()
                except Exception:
                    # line-wise parse
                    data = None
                    for line in (resp.text or "").splitlines():
                        try:
                            data = json.loads(line)
                            break
                        except Exception:
                            continue
                    if data is None:
                        raise ValueError("Embedding response is not valid JSON")

                if isinstance(data, dict):
                    if "embedding" in data and isinstance(data["embedding"], list):
                        return data["embedding"]
                    if "data" in data and isinstance(data["data"], list):
                        first = data["data"][0]
                        if isinstance(first, dict) and isinstance(first.get("embedding"), list):
                            return first["embedding"]
                    if "embeddings" in data and isinstance(data["embeddings"], list):
                        return data["embeddings"][0]
                raise ValueError("Unknown embedding format: " + str(data))
            except Exception as e:
                logger.debug("Embedding with model %s failed: %s", model_choice, e)
                last_exc = e
                continue

        logger.error("Embedding requests all failed: %s", last_exc)
        raise last_exc or RuntimeError("Embedding request failed")

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass


langchain_ollama_service = LangchainOllamaService()