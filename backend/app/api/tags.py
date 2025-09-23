from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

from app.models.database import get_db
from app.models.chat import Tag, Document, DocumentTag
from app.schemas.tag import (
    TagCreate, TagUpdate, Tag as TagSchema, 
    TagList, DocumentTagAdd, DocumentTagResponse
)

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=TagList)
async def get_tags(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all tags with optional search and pagination."""
    query = select(
        Tag,
        func.count(DocumentTag.document_id).label('document_count')
    ).outerjoin(
        DocumentTag, Tag.id == DocumentTag.tag_id
    ).group_by(Tag.id)
    
    if search:
        query = query.where(Tag.name.ilike(f"%{search}%"))
    
    # Get total count
    count_query = select(func.count()).select_from(Tag)
    if search:
        count_query = count_query.where(Tag.name.ilike(f"%{search}%"))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(Tag.name)
    result = await db.execute(query)
    rows = result.all()
    
    tags = []
    for tag, doc_count in rows:
        tag_dict = tag.__dict__
        tag_dict['document_count'] = doc_count or 0
        tags.append(TagSchema(**tag_dict))
    
    return TagList(tags=tags, total=total)


@router.post("", response_model=TagSchema)
async def create_tag(
    tag_create: TagCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new tag for the current user."""
    # Check if tag with same name exists for this user
    existing = await db.execute(
        select(Tag).where(
            func.lower(Tag.name) == func.lower(tag_create.name)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tag with this name already exists")
    
    tag = Tag(**tag_create.model_dump())
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    
    # Add document count
    tag_dict = tag.__dict__
    tag_dict['document_count'] = 0
    
    return TagSchema(**tag_dict)


@router.get("/{tag_id}", response_model=TagSchema)
async def get_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific tag by ID for the current user."""
    query = select(
        Tag,
        func.count(DocumentTag.document_id).label('document_count')
    ).outerjoin(
        DocumentTag, Tag.id == DocumentTag.tag_id
    ).group_by(Tag.id)
    
    result = await db.execute(query)
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    tag, doc_count = row
    tag_dict = tag.__dict__
    tag_dict['document_count'] = doc_count or 0
    
    return TagSchema(**tag_dict)


@router.put("/{tag_id}", response_model=TagSchema)
async def update_tag(
    tag_id: UUID,
    tag_update: TagUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a tag for the current user."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # Check if new name conflicts with existing tag for this user
    if tag_update.name and tag_update.name != tag.name:
        existing = await db.execute(
            select(Tag).where(
                and_(
                    func.lower(Tag.name) == func.lower(tag_update.name),
                    Tag.id != tag_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Tag with this name already exists")
    
    # Update fields
    for field, value in tag_update.model_dump(exclude_unset=True).items():
        setattr(tag, field, value)
    
    await db.commit()
    await db.refresh(tag)
    
    # Get document count
    count_result = await db.execute(
        select(func.count()).select_from(DocumentTag).where(DocumentTag.tag_id == tag_id)
    )
    doc_count = count_result.scalar() or 0
    
    tag_dict = tag.__dict__
    tag_dict['document_count'] = doc_count
    
    return TagSchema(**tag_dict)


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a tag for the current user. This will also remove all document associations."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    await db.delete(tag)
    await db.commit()
    
    return {"message": "Tag deleted successfully"}


@router.get("/{tag_id}/documents")
async def get_tag_documents(
    tag_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get all documents with a specific tag for the current user."""
    # Check tag exists
    tag_result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = tag_result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # Get documents with this tag (ensure documents also belong to the user)
    query = select(Document).join(
        DocumentTag, Document.id == DocumentTag.document_id
    ).where(
        DocumentTag.tag_id == tag_id
    ).options(
        selectinload(Document.tags)
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return {
        "tag": TagSchema.model_validate(tag),
        "documents": documents
    }