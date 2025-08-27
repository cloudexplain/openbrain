import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import get_db
from app.models.user import User
from app.core.security import decode_token
from app.core.session import SessionService

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)  # Don't auto-error, we'll check session too


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user = None
    
    # First try session cookie
    session_token = request.cookies.get(SessionService.SESSION_COOKIE_NAME)
    logger.info(f"Session token from cookie: {'present' if session_token else 'missing'}")
    
    if session_token:
        try:
            user = await SessionService.get_user_from_session(db, session_token)
            if user:
                logger.info(f"User authenticated via session: {user.username}")
                # Check if user needs verification (grace period expired)
                if user.needs_verification:
                    logger.warning(f"User {user.username} needs email verification")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Email verification required. Please verify your email to continue.",
                        headers={"X-Verification-Required": "true"}
                    )
                return user
            else:
                logger.warning(f"Session token invalid or expired: {session_token[:8]}...")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Session authentication error: {str(e)}")
    
    # Fall back to JWT token (for backward compatibility)
    if credentials:
        try:
            user_id = decode_token(credentials.credentials)
            if user_id:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    logger.info(f"User authenticated via JWT: {user.username}")
                    # Check if user needs verification (grace period expired)
                    if user.needs_verification:
                        logger.warning(f"User {user.username} needs email verification")
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Email verification required. Please verify your email to continue.",
                            headers={"X-Verification-Required": "true"}
                        )
                    return user
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"JWT authentication error: {str(e)}")
    
    logger.warning("Authentication failed - no valid session or JWT token")
    raise credentials_exception


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user without raising exception if not authenticated"""
    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None
