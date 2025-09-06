from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
<<<<<<< HEAD
from app.config import settings
from app.api import chat, tags, document_tags
=======
from app.config import get_settings

settings = get_settings()
from app.api import chat, tags, document_tags, auth, documents
from app.core.scheduler import session_cleanup_scheduler
>>>>>>> c3de212 (Highlight quotations (#26))
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.project_name,
    description="SecondBrain AI Assistant API with RAG support",
    version="1.0.0"
)

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


@app.get("/")
async def root():
    return {"message": "SecondBrain API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}