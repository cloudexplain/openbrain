from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from app.models.database import get_db
from app.models.chat import Document, Tag, DocumentTag
from app.schemas.tag import DocumentTagAdd, DocumentTagResponse, Tag as TagSchema

router = APIRouter(prefix="/documents", tags=["document-tags"])


@router.get("/{document_id}/tags", response_model=DocumentTagResponse)
async def get_document_tags(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all tags for a specific document owned by the current user."""
    # Get document with tags
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.tags))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentTagResponse(
        document_id=document.id,
        tags=[TagSchema.model_validate(tag) for tag in document.tags]
    )


@router.post("/{document_id}/tags", response_model=DocumentTagResponse)
async def add_document_tags(
    document_id: UUID,
    tag_data: DocumentTagAdd,
    db: AsyncSession = Depends(get_db)
):
    """Add tags to a document owned by the current user."""
    # Check document exists
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Verify all tags exist
    tag_result = await db.execute(
        select(Tag).where(Tag.id.in_(tag_data.tag_ids))
    )
    tags = tag_result.scalars().all()
    
    if len(tags) != len(tag_data.tag_ids):
        raise HTTPException(status_code=400, detail="One or more tags not found")
    
    # Get existing tags for this document
    existing_result = await db.execute(
        select(DocumentTag.tag_id).where(DocumentTag.document_id == document_id)
    )
    existing_tag_ids = set(existing_result.scalars().all())
    
    # Add new associations (skip existing ones)
    for tag_id in tag_data.tag_ids:
        if tag_id not in existing_tag_ids:
            doc_tag = DocumentTag(document_id=document_id, tag_id=tag_id)
            db.add(doc_tag)
    
    await db.commit()
    
    # Return updated document with all tags
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.tags))
        .where(Document.id == document_id)
    )
    document = result.scalar_one()
    
    return DocumentTagResponse(
        document_id=document.id,
        tags=[TagSchema.model_validate(tag) for tag in document.tags]
    )


@router.delete("/{document_id}/tags/{tag_id}")
async def remove_document_tag(
    document_id: UUID,
    tag_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Remove a tag from a document owned by the current user."""
    # Verify document exists
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Verify tag exists
    tag_result = await db.execute(
        select(Tag).where(Tag.id == tag_id)
    )
    if not tag_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # Check if association exists
    result = await db.execute(
        select(DocumentTag).where(
            (DocumentTag.document_id == document_id) &
            (DocumentTag.tag_id == tag_id)
        )
    )
    doc_tag = result.scalar_one_or_none()
    
    if not doc_tag:
        raise HTTPException(status_code=404, detail="Document-tag association not found")
    
    await db.execute(
        delete(DocumentTag).where(
            (DocumentTag.document_id == document_id) &
            (DocumentTag.tag_id == tag_id)
        )
    )
    await db.commit()
    
    return {"message": "Tag removed from document successfully"}


@router.put("/{document_id}/tags", response_model=DocumentTagResponse)
async def set_document_tags(
    document_id: UUID,
    tag_data: DocumentTagAdd,
    db: AsyncSession = Depends(get_db)
):
    """Replace all tags for a document owned by the current user (complete replacement)."""
    # Check document exists
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Verify all new tags exist
    if tag_data.tag_ids:
        tag_result = await db.execute(
            select(Tag).where(Tag.id.in_(tag_data.tag_ids))
        )
        tags = tag_result.scalars().all()
        
        if len(tags) != len(tag_data.tag_ids):
            raise HTTPException(status_code=400, detail="One or more tags not found")
    
    # Remove all existing tags
    await db.execute(
        delete(DocumentTag).where(DocumentTag.document_id == document_id)
    )
    
    # Add new tags
    for tag_id in tag_data.tag_ids:
        doc_tag = DocumentTag(document_id=document_id, tag_id=tag_id)
        db.add(doc_tag)
    
    await db.commit()
    
    # Return updated document with new tags
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.tags))
        .where(Document.id == document_id)
    )
    document = result.scalar_one()
    
    return DocumentTagResponse(
        document_id=document.id,
        tags=[TagSchema.model_validate(tag) for tag in document.tags]
    )
