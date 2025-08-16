from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json
import asyncio
import os
import aiofiles
from pathlib import Path
from uuid import uuid4

from app.models.database import get_db
from app.schemas.chat import (
    Chat, ChatCreate, ChatUpdate, ChatListItem, 
    ChatRequest, StreamResponse, Message
)
from app.services.chat_service import ChatService
from app.services.embedding_service import embedding_service

router = APIRouter()


@router.get("/chats", response_model=List[ChatListItem])
async def get_chats(db: AsyncSession = Depends(get_db)):
    """Get all chats"""
    return await ChatService.get_chats(db)


@router.post("/chats")
async def create_chat(
    chat_data: ChatCreate, 
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat"""
    db_chat = await ChatService.create_chat(db, chat_data)
    
    # Return manual dict instead of relying on Pydantic model conversion
    return {
        "id": str(db_chat.id),
        "title": db_chat.title,
        "created_at": db_chat.created_at.isoformat() if db_chat.created_at else None,
        "updated_at": db_chat.updated_at.isoformat() if db_chat.updated_at else None,
        "messages": []  # New chats have no messages
    }


@router.get("/chats/{chat_id}", response_model=Chat)
async def get_chat(
    chat_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    """Get a specific chat with messages"""
    chat = await ChatService.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.delete("/chats/{chat_id}")
async def delete_chat(
    chat_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat"""
    success = await ChatService.delete_chat(db, chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"message": "Chat deleted successfully"}


@router.post("/chat")
async def chat_with_ai(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send a message and get AI response (streaming)"""
    try:
        # Get or create chat
        chat = await ChatService.get_or_create_chat(
            db, 
            request.chat_id, 
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message
        )
        
        async def generate_stream():
            try:
                async for chunk, message_id in ChatService.generate_response(
                    db, 
                    chat.id, 
                    request.message,
                    use_rag=request.use_rag,
                    rag_limit=request.rag_limit,
                    rag_threshold=request.rag_threshold
                ):
                    if chunk:
                        # Send content chunk
                        response = StreamResponse(
                            type="content",
                            content=chunk,
                            chat_id=chat.id
                        )
                        yield f"data: {response.model_dump_json()}\n\n"
                    
                    if message_id:
                        # Send completion message
                        response = StreamResponse(
                            type="done",
                            message_id=message_id,
                            chat_id=chat.id
                        )
                        yield f"data: {response.model_dump_json()}\n\n"
                        break
                        
            except Exception as e:
                # Send error message
                error_response = StreamResponse(
                    type="error",
                    error=str(e),
                    chat_id=chat.id
                )
                yield f"data: {error_response.model_dump_json()}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}/messages", response_model=List[Message])
async def get_chat_messages(
    chat_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all messages for a specific chat"""
    chat = await ChatService.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    return sorted(chat.messages, key=lambda x: x.created_at)


@router.post("/chats/{chat_id}/save-to-knowledge")
async def save_chat_to_knowledge(
    chat_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Save a chat conversation to the vector knowledge base"""
    # Get the chat with all messages
    chat = await ChatService.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if not chat.messages:
        raise HTTPException(status_code=400, detail="Chat has no messages to process")
    
    try:
        # Process the chat into unified document/chunks
        chat_document, document_chunks = embedding_service.process_chat_for_knowledge(db, chat)
        
        if not chat_document or not document_chunks:
            raise HTTPException(status_code=400, detail="No chunks could be generated from this chat")
        
        # Save document first
        db.add(chat_document)
        await db.flush()  # Get the document ID
        
        # Associate chunks with document and save
        for chunk in document_chunks:
            chunk.document_id = chat_document.id
            db.add(chunk)
        
        await db.commit()
        
        return {
            "message": f"Successfully saved chat as document with {len(document_chunks)} chunks",
            "chat_id": chat_id,
            "document_id": str(chat_document.id),
            "chunks_created": len(document_chunks)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process chat: {str(e)}")


@router.post("/chats/{chat_id}/save-to-knowledge-edited")
async def save_edited_chat_to_knowledge(
    chat_id: UUID,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Save an edited chat conversation to the vector knowledge base"""
    from app.models.chat import Document, DocumentChunk
    import json
    
    title = request.get("title", "Untitled Document")
    mode = request.get("mode", "document")
    
    try:
        if mode == "document":
            # Single document mode - just save the content as is
            content = request.get("content", "")
            
            # Create document
            chat_document = Document(
                title=title,
                source_type="chat",
                source_id=str(chat_id),
                document_metadata=json.dumps({
                    "chat_id": str(chat_id),
                    "edit_mode": "document",
                    "original_title": title
                })
            )
            
            # Create chunks from the edited content
            chunks = embedding_service.text_splitter.split_text(content)
            
            # Generate embeddings
            if chunks:
                embeddings = embedding_service.embed_texts(chunks)
            else:
                embeddings = []
            
            # Save document
            db.add(chat_document)
            await db.flush()
            
            # Create and save chunks
            document_chunks = []
            for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
                token_count = embedding_service.count_tokens(chunk_content)
                
                document_chunk = DocumentChunk(
                    document_id=chat_document.id,
                    content=chunk_content,
                    chunk_index=i,
                    token_count=token_count,
                    embedding=embedding,
                    chunk_metadata=json.dumps({
                        "source_type": "chat",
                        "chat_id": str(chat_id),
                        "edit_mode": "document"
                    })
                )
                db.add(document_chunk)
                document_chunks.append(document_chunk)
                
        else:
            # Messages mode - reconstruct from edited messages
            messages = request.get("messages", [])
            
            # Create document
            chat_document = Document(
                title=title,
                source_type="chat",
                source_id=str(chat_id),
                document_metadata=json.dumps({
                    "chat_id": str(chat_id),
                    "edit_mode": "messages",
                    "message_count": len(messages),
                    "original_title": title
                })
            )
            
            # Build content from messages
            content_parts = []
            for msg in messages:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                content_parts.append(f"{role_label}:\n{msg['content']}")
            
            full_content = "\n\n".join(content_parts)
            
            # Create chunks
            chunks = embedding_service.text_splitter.split_text(full_content)
            
            # Generate embeddings
            if chunks:
                embeddings = embedding_service.embed_texts(chunks)
            else:
                embeddings = []
            
            # Save document
            db.add(chat_document)
            await db.flush()
            
            # Create and save chunks
            document_chunks = []
            for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
                token_count = embedding_service.count_tokens(chunk_content)
                
                document_chunk = DocumentChunk(
                    document_id=chat_document.id,
                    content=chunk_content,
                    chunk_index=i,
                    token_count=token_count,
                    embedding=embedding,
                    chunk_metadata=json.dumps({
                        "source_type": "chat",
                        "chat_id": str(chat_id),
                        "edit_mode": "messages"
                    })
                )
                db.add(document_chunk)
                document_chunks.append(document_chunk)
        
        await db.commit()
        
        return {
            "message": f"Successfully saved edited document with {len(document_chunks)} chunks",
            "chat_id": str(chat_id),
            "document_id": str(chat_document.id),
            "chunks_created": len(document_chunks)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save edited chat: {str(e)}")


@router.post("/search")
async def search_knowledge(
    query: str,
    limit: int = 5,
    similarity_threshold: float = 0.7,
    source_types: List[str] = None,  # e.g., ['chat', 'file']
    db: AsyncSession = Depends(get_db)
):
    """Search across all knowledge (chats, documents, etc.) using vector similarity"""
    try:
        results = await embedding_service.similarity_search(
            db=db,
            query=query,
            limit=limit,
            similarity_threshold=similarity_threshold,
            source_types=source_types
        )
        
        # Format results for response
        search_results = []
        for chunk in results:
            chunk_metadata = json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {}
            
            result = {
                "id": str(chunk.id),
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "summary": chunk.summary,
                "distance": getattr(chunk, 'search_distance', None),
                "document": {
                    "id": str(chunk.document_id),
                    "title": getattr(chunk, 'document_title', None),
                    "source_type": getattr(chunk, 'source_type', None),
                    "source_id": getattr(chunk, 'source_id', None)
                },
                "metadata": chunk_metadata,
                "created_at": chunk.created_at.isoformat() if chunk.created_at else None
            }
            
            search_results.append(result)
        
        return {
            "query": query,
            "results": search_results,
            "total_results": len(search_results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/documents")
async def get_documents(
    db: AsyncSession = Depends(get_db)
):
    """Get all documents in the knowledge base"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.chat import Document
    
    try:
        result = await db.execute(
            select(Document).options(selectinload(Document.chunks))
        )
        documents = result.scalars().all()
        
        return [
            {
                "id": str(doc.id),
                "title": doc.title,
                "source_type": doc.source_type,
                "source_id": doc.source_id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                "chunk_count": len(doc.chunks),
                "metadata": json.loads(doc.document_metadata) if doc.document_metadata else {}
            }
            for doc in documents
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")


@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific document with all its chunks (full content)"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.chat import Document
    
    print("Calling documents/document_id")
    try:
        result = await db.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.chunks))
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Reconstruct full content from chunks
        sorted_chunks = sorted(document.chunks, key=lambda x: x.chunk_index)
        full_content = "\n\n".join([chunk.content for chunk in sorted_chunks])
        
        return {
            "id": str(document.id),
            "title": document.title,
            "source_type": document.source_type,
            "source_id": document.source_id,
            "filename": document.filename,
            "file_type": document.file_type,
            "content": full_content,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "chunk_count": len(document.chunks),
            "metadata": json.loads(document.document_metadata) if document.document_metadata else {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch document: {str(e)}")


@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a document with individual chunks for editing"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.chat import Document
    
    try:
        result = await db.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.chunks))
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Return chunks individually
        sorted_chunks = sorted(document.chunks, key=lambda x: x.chunk_index)
        
        return {
            "id": str(document.id),
            "title": document.title,
            "source_type": document.source_type,
            "source_id": document.source_id,
            "chunks": [
                {
                    "id": str(chunk.id),
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                    "summary": chunk.summary,
                    "metadata": json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {}
                }
                for chunk in sorted_chunks
            ],
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "metadata": json.loads(document.document_metadata) if document.document_metadata else {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch document chunks: {str(e)}")


@router.put("/documents/{document_id}/chunks")
async def update_document_chunks(
    document_id: UUID,
    chunks_update: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update chunks in a document"""
    from sqlalchemy import select, update
    from app.models.chat import Document, DocumentChunk
    
    try:
        # Verify document exists
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Update title if provided
        if "title" in chunks_update:
            document.title = chunks_update["title"]
        
        # Update chunks
        updated_chunks = []
        if "chunks" in chunks_update:
            for chunk_data in chunks_update["chunks"]:
                chunk_id = UUID(chunk_data["id"])
                
                # Update chunk content
                result = await db.execute(
                    select(DocumentChunk).where(DocumentChunk.id == chunk_id)
                )
                chunk = result.scalar_one_or_none()
                
                if chunk is not None and chunk.document_id == document_id:
                    chunk.content = chunk_data["content"]
                    
                    # Re-generate embedding for updated chunk
                    chunk.embedding = embedding_service.embed_text(chunk_data["content"])
                    
                    # Update token count
                    chunk.token_count = len(chunk_data["content"].split())  # Simple approximation
                    
                    updated_chunks.append(str(chunk_id))
        
        await db.commit()
        
        return {
            "message": "Document updated successfully",
            "updated_chunks": updated_chunks,
            "document_id": str(document_id)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")


async def process_document_background(
    file_path: str,
    original_filename: str,
    file_type: str,
    upload_id: str
):
    """Background task to process uploaded document"""
    from app.models.database import AsyncSessionLocal
    
    try:
        # Create a new database session for the background task
        async with AsyncSessionLocal() as db:
            # Process the document using the embedding service
            document_id, chunks_created = await embedding_service.process_uploaded_document(
                db=db,
                file_path=file_path,
                original_filename=original_filename,
                file_type=file_type
            )
            
            # Store success status (you could store this in Redis or a status table)
            print(f"Successfully processed document: {document_id}, created {chunks_created} chunks")
            
    except Exception as e:
        # Clean up file if processing failed
        if Path(file_path).exists():
            Path(file_path).unlink()
        print(f"Failed to process document: {str(e)}")
        raise


@router.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document file and process it asynchronously in the background"""
    
    # Validate file type
    allowed_types = {
        'application/pdf': '.pdf',
        'text/plain': '.txt',
        'text/markdown': '.md',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file.content_type}. Supported types: PDF, TXT, MD, DOCX"
        )
    
    # Validate file size (50MB max)
    max_size = 50 * 1024 * 1024  # 50MB
    if file.size and file.size > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")
    
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("/app/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename and upload ID
        file_extension = allowed_types[file.content_type]
        upload_id = str(uuid4())
        unique_filename = f"{upload_id}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save file to disk first
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Add background task to process the document
        background_tasks.add_task(
            process_document_background,
            str(file_path),
            file.filename,
            file.content_type,
            upload_id
        )
        
        # Return immediately with upload ID
        return {
            "message": f"File '{file.filename}' uploaded successfully. Processing in background...",
            "upload_id": upload_id,
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")
