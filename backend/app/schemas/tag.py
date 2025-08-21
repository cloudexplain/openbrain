from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    color: str = Field(default='#808080', pattern=r'^#[0-9a-fA-F]{6}$')


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')


class Tag(TagBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    document_count: Optional[int] = 0  # Will be populated in queries
    
    class Config:
        from_attributes = True


class TagList(BaseModel):
    tags: List[Tag]
    total: int


class DocumentTagAdd(BaseModel):
    tag_ids: List[UUID]


class DocumentTagResponse(BaseModel):
    document_id: UUID
    tags: List[Tag]
    
    class Config:
        from_attributes = True