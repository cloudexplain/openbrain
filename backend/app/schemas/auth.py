from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID
import re


class UserLogin(BaseModel):
    username: str  # Can be username or email
    password: str


class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str
    
    @field_validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, hyphens and underscores')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v) > 50:
            raise ValueError('Username must be less than 50 characters')
        return v
    
    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    id: UUID
    username: str
    email: Optional[str] = None
    is_verified: bool
    created_at: datetime
    verification_grace_expires_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('id')
    def serialize_uuid(self, value: UUID) -> str:
        return str(value)


class UserInDB(User):
    password_hash: str