import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.models.database import create_session_local
from app.core.session import SessionService

logger = logging.getLogger(__name__)


class SessionCleanupScheduler:
    """Background scheduler for session cleanup tasks"""
    
    def __init__(self, cleanup_interval_hours: int = 6):
        self.cleanup_interval_hours = cleanup_interval_hours
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the background cleanup scheduler"""
        if self._running:
            logger.warning("Session cleanup scheduler is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"Started session cleanup scheduler (runs every {self.cleanup_interval_hours} hours)")
    
    async def stop(self):
        """Stop the background cleanup scheduler"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped session cleanup scheduler")
    
    async def _cleanup_loop(self):
        """Main cleanup loop that runs periodically"""
        while self._running:
            try:
                await self._perform_cleanup()
                # Sleep for the specified interval
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {str(e)}")
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def _perform_cleanup(self):
        """Perform the actual cleanup operations"""
        try:
            session_local, engine = create_session_local()
            async with session_local() as db:
                try:
                    # Clean up expired sessions
                    expired_count = await SessionService.cleanup_expired_sessions(db)
                    
                    # Clean up inactive sessions (older than 30 days)
                    inactive_count = await SessionService.cleanup_inactive_sessions(db, inactive_days=30)
                    
                    total_cleaned = expired_count + inactive_count
                    
                    if total_cleaned > 0:
                        logger.info(f"Session cleanup: removed {expired_count} expired and {inactive_count} inactive sessions")
                    else:
                        logger.debug("Session cleanup: no sessions to clean")
                        
                finally:
                    await engine.dispose()
                    
        except Exception as e:
            logger.error(f"Failed to perform session cleanup: {str(e)}")
    
    async def manual_cleanup(self) -> dict:
        """Manually trigger a cleanup and return results"""
        try:
            session_local, engine = create_session_local()
            async with session_local() as db:
                try:
                    expired_count = await SessionService.cleanup_expired_sessions(db)
                    inactive_count = await SessionService.cleanup_inactive_sessions(db, inactive_days=30)
                    
                    return {
                        "expired_sessions_cleaned": expired_count,
                        "inactive_sessions_cleaned": inactive_count,
                        "total_cleaned": expired_count + inactive_count,
                        "cleanup_time": datetime.utcnow().isoformat()
                    }
                finally:
                    await engine.dispose()
                    
        except Exception as e:
            logger.error(f"Manual session cleanup failed: {str(e)}")
            return {
                "error": str(e),
                "cleanup_time": datetime.utcnow().isoformat()
            }


# Global scheduler instance
session_cleanup_scheduler = SessionCleanupScheduler()