import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import get_db

logger = logging.getLogger(__name__)

# No authentication required - all endpoints are now public
