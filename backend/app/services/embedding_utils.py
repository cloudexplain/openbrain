from typing import List, Optional
import logging

from app.config import settings
from app.services.reembed_queue import enqueue_reembed
from app.services.langchain import LangchainOllamaService

logger = logging.getLogger(__name__)

def pad_or_truncate(vec: Optional[List[float]], target_dim: int) -> List[float]:
    v = vec or []
    if len(v) == target_dim:
        return v
    if len(v) < target_dim:
        return v + [0.0] * (target_dim - len(v))
    return v[:target_dim]

async def resize_embedding_and_maybe_reembed(
    text: str,
    current_vec: Optional[List[float]],
    current_dim: Optional[int],
    target_dim: int,
    doc_id: str,
    force_sync_on_shrink: bool = True
) -> List[float]:
    cur = current_dim or (len(current_vec) if current_vec else 0)
    if cur == target_dim:
        return current_vec or []

    # Upscale: pad immediately, enqueue background reembed
    if cur < target_dim:
        padded = pad_or_truncate(current_vec, target_dim)
        enqueue_reembed(doc_id=doc_id, text=text, priority=False)
        return padded

    # Downscale: prefer synchronous re-embed for quality
    if cur > target_dim:
        if force_sync_on_shrink:
            svc = LangchainOllamaService(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                embedding_model=settings.embedding_model_resolved,
            )
            new = svc.embed(text)
            return pad_or_truncate(new, target_dim)
        else:
            enqueue_reembed(doc_id=doc_id, text=text, priority=True)
            return pad_or_truncate(current_vec, target_dim)