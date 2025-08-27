from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime

from .base import Base


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    verification_token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    resend_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="email_verifications")
    
    @property
    def is_expired(self) -> bool:
        """Check if verification token has expired"""
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)
    
    @property
    def is_valid(self) -> bool:
        """Check if verification token is valid (active, not expired, not used)"""
        return self.is_active and not self.is_expired and self.used_at is None


class EmailResendTracking(Base):
    __tablename__ = "email_resend_tracking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    attempt_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="email_resend_tracking")