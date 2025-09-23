from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import json
from pathlib import Path

from app.models.database import get_db
from app.models.chat import Document, DocumentChunk

router = APIRouter()


@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get document details with metadata"""
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.tags))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Parse metadata
    metadata = json.loads(document.document_metadata) if document.document_metadata else {}
    
    return {
        "id": str(document.id),
        "title": document.title,
        "source_type": document.source_type,
        "source_id": document.source_id,
        "filename": document.filename,
        "file_type": document.file_type,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "metadata": metadata,
        "tags": [{"id": str(tag.id), "name": tag.name} for tag in document.tags]
    }


@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: UUID,
    chunk_ids: Optional[str] = Query(None, description="Comma-separated chunk IDs to filter"),
    db: AsyncSession = Depends(get_db)
):
    """Get chunks for a specific document, optionally filtered by chunk IDs"""

    # Debug logging
    print(f"🔍 API called with document_id: {document_id}")
    print(f"🔍 API called with chunk_ids parameter: {chunk_ids}")

    # Verify document exists
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Build query for chunks
    if chunk_ids:
        # If chunk_ids provided, filter by them directly
        chunk_id_list = [UUID(cid.strip()) for cid in chunk_ids.split(",")]
        print(f"🔍 Filtering chunks by specific IDs: {chunk_id_list}")
        query = select(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.id.in_(chunk_id_list)
        )
    else:
        # No chunk_ids, get all chunks for document
        print(f"🔍 Getting all chunks for document")
        query = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    
    # Order by chunk index
    query = query.order_by(DocumentChunk.chunk_index)
    
    result = await db.execute(query)
    chunks = result.scalars().all()
    
    # Debug logging
    print(f"🔍 Query returned {len(chunks)} chunks")
    if chunk_ids and len(chunks) > 0:
        print(f"🔍 First chunk ID: {chunks[0].id}")
    
    # Format response with metadata
    chunk_data = []
    for chunk in chunks:
        metadata = json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {}
        
        chunk_data.append({
            "id": str(chunk.id),
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "token_count": chunk.token_count,
            "metadata": metadata,
            "page_number": metadata.get("page_number"),  # Extract page if available
            "created_at": chunk.created_at.isoformat() if chunk.created_at else None
        })
    
    return {
        "document_id": str(document_id),
        "document_title": document.title,
        "total_chunks": len(chunk_data),
        "chunks": chunk_data
    }


@router.get("/documents/{document_id}/file")
async def get_document_file(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the actual file for a document (if it's a file-based document)"""

    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.source_type != "file":
        raise HTTPException(status_code=400, detail="Document is not file-based")
    
    # Parse metadata to get file path
    metadata = json.loads(document.document_metadata) if document.document_metadata else {}
    file_path = metadata.get("file_path")
    
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Return file
    return FileResponse(
        path=file_path,
        filename=document.filename or f"document_{document_id}",
        media_type=document.file_type or "application/octet-stream"
    )


@router.get("/documents")
async def list_documents(
    source_type: Optional[str] = Query(None, description="Filter by source type (file, chat, url)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List all documents"""

    query = select(Document)
    
    # Apply source type filter if provided
    if source_type:
        query = query.where(Document.source_type == source_type)
    
    # Order by creation date (newest first) and apply pagination
    query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    # Format response
    docs_data = []
    for doc in documents:
        metadata = json.loads(doc.document_metadata) if doc.document_metadata else {}
        
        docs_data.append({
            "id": str(doc.id),
            "title": doc.title,
            "source_type": doc.source_type,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "metadata": metadata
        })
    
    return {
        "total": len(docs_data),
        "offset": offset,
        "limit": limit,
        "documents": docs_data
    }