import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from fastapi import Request, Response, HTTPException, status

from app.models.session import Session
from app.models.user import User


class SessionService:
    # Session configuration
    SESSION_COOKIE_NAME = "sessionid"
    SESSION_DURATION_HOURS = 24 * 7  # 7 days
    SESSION_TOKEN_LENGTH = 32  # bytes, will be hex encoded to 64 chars
    
    @classmethod
    def generate_session_token(cls) -> str:
        """Generate a cryptographically secure session token"""
        return secrets.token_hex(cls.SESSION_TOKEN_LENGTH)
    
    @classmethod
    async def create_session(
        cls,
        db: AsyncSession,
        user_id: str,
        request: Request
    ) -> Session:
        """Create a new session for a user"""
        # Extract request metadata
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500]  # Limit length
        
        # Generate session token
        session_token = cls.generate_session_token()
        
        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(hours=cls.SESSION_DURATION_HOURS)
        
        # Create session
        session = Session(
            session_token=session_token,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        return session
    
    @classmethod
    async def get_session(
        cls,
        db: AsyncSession,
        session_token: str
    ) -> Optional[Session]:
        """Get a valid session by token"""
        result = await db.execute(
            select(Session)
            .where(
                and_(
                    Session.session_token == session_token,
                    Session.is_active == True
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if session and session.is_valid:
            # Update last activity
            session.last_activity = datetime.utcnow()
            await db.commit()
            return session
        
        return None
    
    @classmethod
    async def get_user_from_session(
        cls,
        db: AsyncSession,
        session_token: str
    ) -> Optional[User]:
        """Get user from session token"""
        session = await cls.get_session(db, session_token)
        if not session:
            return None
        
        # Get user
        result = await db.execute(
            select(User).where(User.id == session.user_id)
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def invalidate_session(
        cls,
        db: AsyncSession,
        session_token: str
    ) -> bool:
        """Invalidate a session"""
        result = await db.execute(
            select(Session).where(Session.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        
        if session:
            session.is_active = False
            await db.commit()
            return True
        
        return False
    
    @classmethod
    async def invalidate_all_user_sessions(
        cls,
        db: AsyncSession,
        user_id: str
    ) -> int:
        """Invalidate all sessions for a user"""
        result = await db.execute(
            select(Session).where(
                and_(
                    Session.user_id == user_id,
                    Session.is_active == True
                )
            )
        )
        sessions = result.scalars().all()
        
        count = 0
        for session in sessions:
            session.is_active = False
            count += 1
        
        await db.commit()
        return count
    
    @classmethod
    async def cleanup_expired_sessions(
        cls,
        db: AsyncSession
    ) -> int:
        """Remove expired sessions from database"""
        result = await db.execute(
            delete(Session).where(
                Session.expires_at < datetime.utcnow()
            )
        )
        await db.commit()
        return result.rowcount
    
    @classmethod
    def set_session_cookie(
        cls,
        response: Response,
        session_token: str
    ):
        """Set session cookie in response"""
        # Determine if we're in production (would have proper env detection in real app)
        from app.config import get_settings
        is_production = "localhost" not in get_settings().database_url
        
        response.set_cookie(
            key=cls.SESSION_COOKIE_NAME,
            value=session_token,
            httponly=True,  # Prevent JS access
            secure=is_production,  # HTTPS only in production, HTTP OK for dev
            samesite="lax",  # CSRF protection
            max_age=cls.SESSION_DURATION_HOURS * 3600  # Convert to seconds
        )
    
    @classmethod
    def clear_session_cookie(cls, response: Response):
        """Clear session cookie"""
        from app.config import get_settings
        is_production = "localhost" not in get_settings().database_url
        
        response.delete_cookie(
            key=cls.SESSION_COOKIE_NAME,
            secure=is_production,
            samesite="lax"
        )
    
    @classmethod
    async def cleanup_expired_sessions_for_user(
        cls,
        db: AsyncSession,
        user_id: str
    ) -> int:
        """Remove expired sessions for a specific user"""
        result = await db.execute(
            delete(Session).where(
                and_(
                    Session.user_id == user_id,
                    Session.expires_at < datetime.utcnow()
                )
            )
        )
        await db.commit()
        return result.rowcount
    
    @classmethod
    async def get_active_sessions_for_user(
        cls,
        db: AsyncSession,
        user_id: str,
        limit: int = 10
    ) -> list:
        """Get active sessions for a user with metadata"""
        result = await db.execute(
            select(Session)
            .where(
                and_(
                    Session.user_id == user_id,
                    Session.is_active == True,
                    Session.expires_at > datetime.utcnow()
                )
            )
            .order_by(Session.last_activity.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @classmethod
    async def cleanup_inactive_sessions(
        cls,
        db: AsyncSession,
        inactive_days: int = 30
    ) -> int:
        """Remove sessions that have been inactive for specified days"""
        inactive_threshold = datetime.utcnow() - timedelta(days=inactive_days)
        
        result = await db.execute(
            delete(Session).where(
                Session.last_activity < inactive_threshold
            )
        )
        await db.commit()
        return result.rowcount