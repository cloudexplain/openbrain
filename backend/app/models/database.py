from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .base import Base
from app.config import get_settings

# Global engine and session maker
engine = create_async_engine(
    get_settings().database_url,
    echo=True,  # Set to False in production
    future=True
)
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

def create_session_local():
    """Return the global session factory for background tasks."""
    return async_session_maker, engine


async def get_db() -> AsyncSession:
    """FastAPI dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

# Function to dispose of the engine when the application shuts down
async def dispose_db_engine():
    await engine.dispose()