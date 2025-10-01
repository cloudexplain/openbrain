from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class FolderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    color: str = Field(default="#4F46E5", pattern="^#[0-9A-Fa-f]{6}$")
    parent_id: Optional[uuid.UUID] = None


class FolderCreate(FolderBase):
    pass


class FolderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    parent_id: Optional[uuid.UUID] = None


class FolderMove(BaseModel):
    parent_id: Optional[uuid.UUID] = None


class FolderInDB(FolderBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Folder(FolderInDB):
    children: List['Folder'] = []
    document_count: int = 0


class FolderWithDocuments(Folder):
    pass


# Update forward references
Folder.model_rebuild()