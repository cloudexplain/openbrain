"""Service for managing email verification tokens and flow"""
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update

from app.models.user import User
from app.models.email_verification import EmailVerification, EmailResendTracking
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)


class VerificationService:
    """Manages email verification tokens and processes"""
    
    TOKEN_LENGTH = 32  # bytes, will be hex encoded to 64 chars
    TOKEN_EXPIRY_HOURS = 24
    GRACE_PERIOD_HOURS = 24
    
    # Rate limiting configuration
    MAX_RESENDS_PER_HOUR = 3
    MAX_RESENDS_PER_DAY = 10
    
    # User limit
    MAX_TOTAL_USERS = 100
    
    @classmethod
    def generate_verification_token(cls) -> str:
        """Generate a cryptographically secure verification token"""
        return secrets.token_urlsafe(cls.TOKEN_LENGTH)
    
    @classmethod
    async def check_user_limit(cls, db: AsyncSession) -> Tuple[bool, int]:
        """Check if we've reached the user limit"""
        result = await db.execute(select(func.count(User.id)))
        user_count = result.scalar()
        return user_count < cls.MAX_TOTAL_USERS, user_count
    
    @classmethod
    async def create_verification_token(
        cls,
        db: AsyncSession,
        user_id: str,
        email: str
    ) -> EmailVerification:
        """Create a new verification token for a user"""
        
        # Invalidate any existing active tokens for this user
        await db.execute(
            update(EmailVerification)
            .where(and_(
                EmailVerification.user_id == user_id,
                EmailVerification.is_active == True
            ))
            .values(is_active=False)
        )
        
        # Generate new token
        token = cls.generate_verification_token()
        expires_at = datetime.utcnow() + timedelta(hours=cls.TOKEN_EXPIRY_HOURS)
        
        # Create verification record
        verification = EmailVerification(
            user_id=user_id,
            email=email,
            verification_token=token,
            expires_at=expires_at,
            is_active=True,
            resend_count=0
        )
        
        db.add(verification)
        await db.commit()
        await db.refresh(verification)
        
        return verification
    
    @classmethod
    async def verify_token(
        cls,
        db: AsyncSession,
        token: str
    ) -> Optional[User]:
        """Verify a token and mark user as verified"""
        
        # Find valid verification token
        result = await db.execute(
            select(EmailVerification)
            .where(and_(
                EmailVerification.verification_token == token,
                EmailVerification.is_active == True
            ))
        )
        verification = result.scalar_one_or_none()
        
        if not verification:
            logger.warning(f"Invalid verification token attempted: {token[:8]}...")
            return None
        
        if not verification.is_valid:
            if verification.is_expired:
                logger.warning(f"Expired verification token used: {token[:8]}...")
            return None
        
        # Get the user
        result = await db.execute(
            select(User).where(User.id == verification.user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User not found for verification token: {verification.user_id}")
            return None
        
        # Mark user as verified
        user.is_verified = True
        user.email_verified_at = datetime.utcnow()
        
        # Mark token as used
        verification.used_at = datetime.utcnow()
        verification.is_active = False
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User {user.username} successfully verified email {user.email}")
        return user
    
    @classmethod
    async def check_resend_rate_limit(
        cls,
        db: AsyncSession,
        user_id: str
    ) -> Tuple[bool, dict]:
        """Check if user has exceeded rate limits for resending verification emails"""
        
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Count attempts in last hour
        hour_result = await db.execute(
            select(func.count(EmailResendTracking.id))
            .where(and_(
                EmailResendTracking.user_id == user_id,
                EmailResendTracking.attempt_time > hour_ago
            ))
        )
        hour_count = hour_result.scalar()
        
        # Count attempts in last day
        day_result = await db.execute(
            select(func.count(EmailResendTracking.id))
            .where(and_(
                EmailResendTracking.user_id == user_id,
                EmailResendTracking.attempt_time > day_ago
            ))
        )
        day_count = day_result.scalar()
        
        # Check limits
        if hour_count >= cls.MAX_RESENDS_PER_HOUR:
            return False, {
                "reason": "hourly_limit",
                "message": f"Maximum {cls.MAX_RESENDS_PER_HOUR} resend attempts per hour exceeded",
                "retry_after": 3600  # seconds
            }
        
        if day_count >= cls.MAX_RESENDS_PER_DAY:
            return False, {
                "reason": "daily_limit",
                "message": f"Maximum {cls.MAX_RESENDS_PER_DAY} resend attempts per day exceeded",
                "retry_after": 86400  # seconds
            }
        
        return True, {
            "attempts_this_hour": hour_count,
            "attempts_today": day_count,
            "remaining_this_hour": cls.MAX_RESENDS_PER_HOUR - hour_count,
            "remaining_today": cls.MAX_RESENDS_PER_DAY - day_count
        }
    
    @classmethod
    async def resend_verification_email(
        cls,
        db: AsyncSession,
        user_id: str,
        base_url: str
    ) -> Tuple[bool, dict]:
        """Resend verification email with rate limiting"""
        
        # Check rate limits
        can_resend, rate_info = await cls.check_resend_rate_limit(db, user_id)
        if not can_resend:
            return False, rate_info
        
        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False, {"message": "User not found"}
        
        if user.is_verified:
            return False, {"message": "User is already verified"}
        
        # Track resend attempt
        tracking = EmailResendTracking(
            user_id=user_id,
            email=user.email
        )
        db.add(tracking)
        
        # Invalidate old tokens and create new one
        verification = await cls.create_verification_token(db, user_id, user.email)
        
        # Update resend count
        verification.resend_count += 1
        await db.commit()
        
        # Generate verification URL
        verification_url = f"{base_url}/verify-email?token={verification.verification_token}"
        
        # Send email
        email_service = get_email_service()
        sent = await email_service.send_verification_email(
            user.email,
            user.username,
            verification_url
        )
        
        if sent:
            logger.info(f"Verification email resent to {user.email}")
            return True, {
                "message": "Verification email sent successfully",
                **rate_info
            }
        else:
            logger.error(f"Failed to resend verification email to {user.email}")
            return False, {"message": "Failed to send email"}
    
    @classmethod
    async def send_initial_verification_email(
        cls,
        db: AsyncSession,
        user: User,
        base_url: str
    ) -> bool:
        """Send initial verification email to new user"""
        
        # Create verification token
        verification = await cls.create_verification_token(
            db, 
            str(user.id), 
            user.email
        )
        
        # Generate verification URL
        verification_url = f"{base_url}/verify-email?token={verification.verification_token}"
        
        # Send email
        email_service = get_email_service()
        sent = await email_service.send_verification_email(
            user.email,
            user.username,
            verification_url
        )
        
        if sent:
            logger.info(f"Initial verification email sent to {user.email}")
        else:
            logger.error(f"Failed to send initial verification email to {user.email}")
        
        return sent
    
    @classmethod
    async def cleanup_expired_tokens(
        cls,
        db: AsyncSession
    ) -> int:
        """Clean up expired verification tokens"""
        
        # Find and delete expired tokens older than 7 days
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        result = await db.execute(
            select(EmailVerification)
            .where(EmailVerification.expires_at < cutoff_date)
        )
        expired_tokens = result.scalars().all()
        
        for token in expired_tokens:
            await db.delete(token)
        
        await db.commit()
        
        return len(expired_tokens)
    
    @classmethod
    async def cleanup_old_tracking_records(
        cls,
        db: AsyncSession,
        days: int = 7
    ) -> int:
        """Clean up old email resend tracking records"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await db.execute(
            select(EmailResendTracking)
            .where(EmailResendTracking.attempt_time < cutoff_date)
        )
        old_records = result.scalars().all()
        
        for record in old_records:
            await db.delete(record)
        
        await db.commit()
        
        return len(old_records)
