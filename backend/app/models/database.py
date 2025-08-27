from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .base import Base


def create_session_local():
    """Create a new session factory for background tasks."""
    from app.config import get_settings
    
    engine = create_async_engine(
        get_settings().database_url,
        echo=True,  # Set to False in production
        future=True
    )
    
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    ), engine


async def get_db() -> AsyncSession:
    """FastAPI dependency to get database session."""
    session_local, engine = create_session_local()
    
    async with session_local() as session:
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()