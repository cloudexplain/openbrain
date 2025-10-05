import asyncio
import logging
from typing import Tuple, Optional

from app.config import settings
from app.models.chat import DocumentChunk
from app.models.database import async_session_maker
from app.services.langchain import LangchainOllamaService

logger = logging.getLogger(__name__)

QUEUE: asyncio.PriorityQueue = asyncio.PriorityQueue()
BATCH_SIZE = 1

def enqueue_reembed(doc_id: str, text: str, priority: bool = False):
    # Priority queue uses (priority_value, item) tuples
    # Lower priority values are processed first
    priority_value = 0 if priority else 1
    item = (str(doc_id), text or "")
    QUEUE.put_nowait((priority_value, item))

async def _process_item(item: Tuple[str, str]):
    doc_id, text = item
    svc = LangchainOllamaService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        embedding_model=settings.embedding_model_resolved,
    )
    try:
        loop = asyncio.get_event_loop()
        emb = await loop.run_in_executor(None, svc.embed, text)
        if emb is None:
            logger.warning("Empty embedding for %s", doc_id)
            return
        async with async_session_maker() as session:
            row = await session.get(DocumentChunk, doc_id)
            if not row:
                logger.debug("DocumentChunk %s not found", doc_id)
                return
            row.embedding = emb
            row.embedding_dim = len(emb)
            row.embedding_model = settings.embedding_model_resolved
            session.add(row)
            await session.commit()
            logger.info("Re-embedded %s dim=%s", doc_id, len(emb))
    except Exception:
        logger.exception("Failed to reembed %s", doc_id)

async def _worker_loop():
    while True:
        priority_item = await QUEUE.get()
        try:
            # Extract the actual item from the priority tuple
            _, item = priority_item
            await _process_item(item)
        finally:
            QUEUE.task_done()

def start_worker(loop: asyncio.AbstractEventLoop):
    loop.create_task(_worker_loop())