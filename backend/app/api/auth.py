from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.database import get_db
from app.models.user import User
from app.schemas.auth import UserLogin, UserSignup, Token, User as UserSchema
from app.core.security import create_access_token
from app.core.utils import verify_password, get_password_hash
from app.core.deps import get_current_user
from app.core.session import SessionService
from app.core.scheduler import session_cleanup_scheduler
from app.services.verification_service import VerificationService
from app.config import get_settings
from datetime import datetime, timedelta

router = APIRouter()
security = HTTPBearer()


@router.post("/signup")
async def signup(
    user_data: UserSignup,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Create a new user account with email verification"""
    
    # Check user limit
    can_add_user, user_count = await VerificationService.check_user_limit(db)
    if not can_add_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Registration is currently closed. Maximum user limit ({VerificationService.MAX_TOTAL_USERS}) has been reached."
        )
    
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    grace_expires = datetime.utcnow() + timedelta(hours=VerificationService.GRACE_PERIOD_HOURS)
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        is_verified=False,
        verification_grace_expires_at=grace_expires
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Send verification email
    settings = get_settings()
    
    print(f"🔧 DEBUG: About to send verification email to {new_user.email}")
    print(f"🔧 DEBUG: Using base URL: {settings.base_url}")
    email_sent = await VerificationService.send_initial_verification_email(db, new_user, settings.base_url)
    print(f"🔧 DEBUG: Email sent result: {email_sent}")
    
    if not email_sent:
        print(f"⚠️ WARNING: Failed to send verification email to {new_user.email}")
    else:
        print(f"✅ SUCCESS: Verification email sent to {new_user.email}")
    
    # Create session for immediate login
    session = await SessionService.create_session(db, str(new_user.id), request)
    SessionService.set_session_cookie(response, session.session_token)
    
    # Create JWT token for backward compatibility
    access_token = create_access_token(subject=str(new_user.id))
    
    return {
        "message": "Account created successfully. Please check your email to verify your account.",
        "user": {
            "id": str(new_user.id),
            "username": new_user.username,
            "email": new_user.email,
            "is_verified": new_user.is_verified,
            "verification_grace_expires_at": new_user.verification_grace_expires_at.isoformat() if new_user.verification_grace_expires_at else None
        },
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/login", response_model=Token)
async def login_for_access_token(
    user_credentials: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    # Find user by username OR email
    # Check if the input looks like an email
    from sqlalchemy import or_
    
    login_field = user_credentials.username.strip().lower()
    
    # Try to find user by username or email
    result = await db.execute(
        select(User).where(
            or_(
                func.lower(User.username) == login_field,
                func.lower(User.email) == login_field
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create session
    session = await SessionService.create_session(db, str(user.id), request)
    
    # Set session cookie
    SessionService.set_session_cookie(response, session.session_token)
    
    # Still return JWT for backward compatibility, but we'll use session
    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer", "session_token": session.session_token}


@router.get("/me", response_model=UserSchema)
async def read_users_me(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Logout and invalidate session"""
    # Get session token from cookie
    session_token = request.cookies.get(SessionService.SESSION_COOKIE_NAME)
    
    if session_token:
        # Invalidate session in database
        await SessionService.invalidate_session(db, session_token)
        
        # Clear session cookie
        SessionService.clear_session_cookie(response)
    
    return {"message": "Successfully logged out"}


@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active sessions for current user"""
    sessions = await SessionService.get_active_sessions_for_user(db, str(current_user.id))
    
    return {
        "sessions": [
            {
                "id": str(session.id),
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "last_activity": session.last_activity.isoformat() if session.last_activity else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None
            }
            for session in sessions
        ]
    }


@router.post("/sessions/cleanup")
async def cleanup_user_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clean up expired sessions for current user"""
    cleaned_count = await SessionService.cleanup_expired_sessions_for_user(db, str(current_user.id))
    
    return {
        "message": f"Cleaned up {cleaned_count} expired sessions",
        "cleaned_sessions": cleaned_count
    }


@router.post("/sessions/logout-all")
async def logout_all_sessions(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout from all sessions for current user"""
    invalidated_count = await SessionService.invalidate_all_user_sessions(db, str(current_user.id))
    
    # Clear current session cookie
    SessionService.clear_session_cookie(response)
    
    return {
        "message": f"Logged out from {invalidated_count} sessions",
        "invalidated_sessions": invalidated_count
    }


@router.post("/admin/sessions/cleanup")
async def manual_session_cleanup():
    """Manually trigger session cleanup (admin endpoint)"""
    result = await session_cleanup_scheduler.manual_cleanup()
    
    return {
        "message": "Manual session cleanup completed",
        **result
    }


@router.post("/verify-email")
async def verify_email(
    token: str,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Verify email address using verification token"""
    
    user = await VerificationService.verify_token(db, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Create new session after successful verification
    session = await SessionService.create_session(db, str(user.id), request)
    SessionService.set_session_cookie(response, session.session_token)
    
    return {
        "message": "Email verified successfully",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "is_verified": user.is_verified
        }
    }


@router.post("/resend-verification")
async def resend_verification_email(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resend verification email with rate limiting"""
    
    if current_user.is_verified:
        return {
            "message": "Email is already verified",
            "is_verified": True
        }
    
    settings = get_settings()
    base_url = settings.base_url
    
    success, info = await VerificationService.resend_verification_email(
        db,
        str(current_user.id),
        base_url
    )
    
    if not success:
        # Check if it's a rate limit error
        if "reason" in info and info["reason"] in ["hourly_limit", "daily_limit"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=info["message"],
                headers={"Retry-After": str(info.get("retry_after", 3600))}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=info.get("message", "Failed to resend verification email")
            )
    
    return info


@router.get("/verification-status")
async def get_verification_status(
    current_user: User = Depends(get_current_user)
):
    """Get current user's verification status"""
    
    return {
        "is_verified": current_user.is_verified,
        "email": current_user.email,
        "needs_verification": current_user.needs_verification,
        "is_within_grace_period": current_user.is_within_grace_period,
        "verification_grace_expires_at": current_user.verification_grace_expires_at.isoformat() if current_user.verification_grace_expires_at else None
    }
