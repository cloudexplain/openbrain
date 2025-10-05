from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.database import dispose_db_engine # Import the dispose function
from app.services.langchain import LangchainOllamaService
from app.services.reembed_queue import start_worker
from app.config import Settings

settings = get_settings()
import logging
import asyncio
from app.api import chat, tags, document_tags, documents, deep_research, folders
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.project_name,
    description="SecondBrain AI Assistant API with RAG support",
    version="1.0.0",
    debug=True
)


# Application lifecycle events

@app.on_event("startup")
async def startup_events():
    # Bestimme embedding_dim falls noch nicht gesetzt
    if settings.embedding_dim is None and settings.llm_provider == "ollama":
        try:
            svc = LangchainOllamaService(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                embedding_model=settings.embedding_model_resolved,
            )
            # Call the helper function to determine dimension
            dim = svc.get_embedding_dimension()
            settings.embedding_dim = int(dim)
            logger.info("Detected embedding_dim=%s for model=%s", settings.embedding_dim, settings.embedding_model_resolved)
        except Exception as e:
            logger.warning("Could not auto-detect embedding_dim: %s. Fallback=1536", e)
            settings.embedding_dim = settings.embedding_dim or 1536

    logger.info("Using embedding model=%s dim=%s", settings.embedding_model_resolved, settings.embedding_dim)

    # start reembed worker
    try:
        start_worker(loop)
        logger.info("Reembed worker started")
    except Exception as e:
        logger.warning("Could not start reembed worker: %s", e)



@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on application shutdown"""
    logger.info("Shutting down SecondBrain API...")
    await dispose_db_engine() # Dispose of the database engine
    logger.info("Application shutdown complete")

# Debug: Log CORS settings
logger.info(f"CORS Origins configured: {settings.cors_origins}")
logger.info(f"Type of cors_origins: {type(settings.cors_origins)}")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug: Log middleware configuration
logger.info("CORS middleware added with following settings:")
logger.info(f"  - allow_origins: {settings.cors_origins}")
logger.info(f"  - allow_credentials: True")
logger.info(f"  - allow_methods: ['*']")
logger.info(f"  - allow_headers: ['*']")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    logger.info(f"Request headers: {dict(request.headers)}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# Include routers

# Can be called via /api/v1/chat
app.include_router(
    chat.router,
    prefix=settings.api_v1_str,
    tags=["chat"]
)

# Tag management routes
app.include_router(
    tags.router,
    prefix=settings.api_v1_str,
    tags=["tags"]
)

# Document-tag association routes
app.include_router(
    document_tags.router,
    prefix=settings.api_v1_str,
    tags=["document-tags"]
)

# Document management routes
app.include_router(
    documents.router,
    prefix=settings.api_v1_str,
    tags=["documents"]
)

# Deep Research routes
app.include_router(
    deep_research.router,
    prefix=settings.api_v1_str + "/deep-research",
    tags=["deep-research"]
)

# Folder management routes
app.include_router(
    folders.router,
    prefix=settings.api_v1_str + "/folders",
    tags=["folders"]
)


@app.get("/")
async def root():
    return {"message": "SecondBrain API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}