from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import StreamingResponse, FileResponse
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
async def get_chats(
    db: AsyncSession = Depends(get_db)
):
    """Get all chats"""
    return await ChatService.get_chats(db, None)


@router.post("/chats")
async def create_chat(
    chat_data: ChatCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat"""
    db_chat = await ChatService.create_chat(db, chat_data, None)
    
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
    chat = await ChatService.get_chat(db, chat_id, None)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.put("/chats/{chat_id}")
async def update_chat(
    chat_id: UUID,
    chat_data: ChatUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a chat's title and/or messages"""
    updated_chat = await ChatService.update_chat(db, chat_id, chat_data, None)
    if not updated_chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return updated_chat


@router.delete("/chats/{chat_id}")
async def delete_chat(
    chat_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat"""
    success = await ChatService.delete_chat(db, chat_id, None)
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
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
            user_id=None
        )
        
        async def generate_stream():
            try:
                async for result in ChatService.generate_response(
                    db,
                    chat.id,
                    request.message,
                    None,
                    use_rag=request.use_rag,
                    rag_limit=request.rag_limit,
                    rag_threshold=request.rag_threshold,
                    use_deep_research=request.use_deep_research,
                    max_concurrent_research_units=request.max_concurrent_research_units,
                    max_researcher_iterations=request.max_researcher_iterations,
                    max_react_tool_calls=request.max_react_tool_calls,
                    max_structured_output_retries=request.max_structured_output_retries
                ):
                    # Handle both 2-tuple, 3-tuple, and 4-tuple returns
                    if len(result) == 2:
                        chunk, message_id = result
                        document_references = None
                        citation_mapping = None
                    elif len(result) == 3:
                        chunk, message_id, document_references = result
                        citation_mapping = None
                    else:
                        chunk, message_id, document_references, citation_mapping = result
                    
                    if chunk:
                        # Send content chunk
                        response = StreamResponse(
                            type="content",
                            content=chunk,
                            chat_id=chat.id
                        )
                        yield f"data: {response.model_dump_json()}\n\n"
                    
                    if message_id:
                        # Send completion message with document references and citation mapping
                        response_data = {
                            "type": "done",
                            "message_id": str(message_id),
                            "chat_id": str(chat.id)
                        }
                        
                        # Add document references if available
                        if document_references:
                            response_data["document_references"] = document_references
                        
                        # Add citation mapping if available
                        if citation_mapping:
                            response_data["citation_mapping"] = citation_mapping
                        
                        yield f"data: {json.dumps(response_data)}\n\n"
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
    chat = await ChatService.get_chat(db, chat_id, None)
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
    chat = await ChatService.get_chat(db, chat_id, None)
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
        # Update the chat title in the database
        from app.models.chat import Chat
        from sqlalchemy import select
        
        chat_result = await db.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        chat = chat_result.scalar_one_or_none()
        
        if chat:
            chat.title = title
            await db.flush()  # Ensure the chat title is updated
        if mode == "document":
            # Single document mode - just save the content as is
            content = request.get("content", "")
            
            # Create document
            chat_document = Document(
                title=title,
                user_id=None,
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
                user_id=None,
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


@router.post("/chats/{chat_id}/auto-update-title")
async def auto_update_chat_title(
    chat_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Automatically generate and update chat title based on recent messages"""
    from app.models.chat import Chat, Message
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    import json
    
    try:
        # Get the chat with its messages
        result = await db.execute(
            select(Chat)
            .where(Chat.id == chat_id)
            .options(selectinload(Chat.messages))
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        if not chat.messages or len(chat.messages) < 2:
            return {"message": "Not enough messages to generate title", "title": chat.title}
        
        # Get the last 3 message pairs (up to 6 messages)
        sorted_messages = sorted(chat.messages, key=lambda x: x.created_at)
        recent_messages = sorted_messages[-6:] if len(sorted_messages) >= 6 else sorted_messages
        
        # Format messages for the prompt
        conversation = "\n".join([
            f"{'User' if msg.role == 'user' else 'Assistant'}: {msg.content[:200]}..."
            if len(msg.content) > 200 else f"{'User' if msg.role == 'user' else 'Assistant'}: {msg.content}"
            for msg in recent_messages
        ])
        
        # Create prompt for title generation
        prompt = f"""Current chat title: "{chat.title}"

Recent conversation:
{conversation}

Based on the recent conversation, should the title be updated? 
Be conservative - only suggest a new title if the conversation has significantly shifted topic or if the current title is generic (like "New Chat").
If the current title already describes the conversation well, keep it.

Respond with ONLY a JSON object in this format:
{{"update": true/false, "title": "suggested title if update is true"}}

The title should be concise (3-7 words), descriptive, and capture the main topic."""

        # Use the Azure OpenAI service for title generation
        from app.services.azure_openai import azure_openai_service
        import re
        
        # Get response from LLM
        response_text = ""
        async for chunk in azure_openai_service.generate_chat_completion(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates concise chat titles based on conversation content. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=100
        ):
            response_text += chunk
        
        # Parse the response
        try:
            # Extract JSON from the response
            json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                if result.get("update") and result.get("title"):
                    # Update the chat title
                    chat.title = result["title"]
                    await db.commit()
                    
                    return {
                        "updated": True,
                        "title": result["title"],
                        "message": "Title updated successfully"
                    }
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Failed to parse title response: {e}, Response: {response_text}")
        
        return {
            "updated": False,
            "title": chat.title,
            "message": "Title remains unchanged"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update title: {str(e)}")


@router.patch("/chats/{chat_id}")
async def update_chat(
    chat_id: UUID,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update chat properties (like title)"""
    from app.models.chat import Chat
    from sqlalchemy import select
    
    try:
        # Get the chat
        result = await db.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Update title if provided
        if "title" in request:
            chat.title = request["title"]
        
        await db.commit()
        
        return {
            "message": "Chat updated successfully",
            "chat_id": str(chat_id),
            "title": chat.title
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update chat: {str(e)}")


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
            user_id=None,
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
    """Get all documents in the knowledge base - metadata only for performance"""
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload
    from app.models.chat import Document, DocumentChunk
    
    try:
        # Get documents with chunk count using a subquery for better performance
        # This avoids loading all chunks into memory
        stmt = select(
            Document,
            func.count(DocumentChunk.id).label('chunk_count')
        ).outerjoin(
            DocumentChunk, Document.id == DocumentChunk.document_id
        ).group_by(Document.id)
        
        result = await db.execute(stmt)
        documents_with_counts = result.all()
        
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
                "chunk_count": chunk_count,
                "metadata": json.loads(doc.document_metadata) if doc.document_metadata else {}
            }
            for doc, chunk_count in documents_with_counts
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
    """Update chunks in a document using full replacement strategy"""
    from sqlalchemy import select, delete
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
        
        # Full replacement strategy: Delete all existing chunks first
        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        
        # Recreate chunks from the update payload
        created_chunks = []
        if "chunks" in chunks_update:
            for index, chunk_data in enumerate(chunks_update["chunks"]):
                chunk_content = chunk_data["content"]
                
                # Generate embedding for the chunk
                embedding = embedding_service.embed_text(chunk_content)
                
                # Calculate token count
                token_count = embedding_service.count_tokens(chunk_content)
                
                # Create new chunk
                new_chunk = DocumentChunk(
                    document_id=document_id,
                    content=chunk_content,
                    chunk_index=index,  # Use enumeration index to ensure proper ordering
                    token_count=token_count,
                    embedding=embedding,
                    chunk_metadata=json.dumps({
                        "source_type": document.source_type,
                        "edited": True,
                        "original_chunk_id": chunk_data.get("id")  # Keep reference to original if needed
                    })
                )
                
                db.add(new_chunk)
                created_chunks.append({
                    "index": index,
                    "content_preview": chunk_content[:100] + "..." if len(chunk_content) > 100 else chunk_content
                })
        
        await db.commit()
        
        return {
            "message": f"Document updated successfully with {len(created_chunks)} chunks",
            "chunks_replaced": len(created_chunks),
            "document_id": str(document_id),
            "title": document.title
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")


import logging # Import logging module

async def process_document_background(
    file_path: str,
    original_filename: str,
    file_type: str,
    upload_id: str,
):
    """Background task to process uploaded document"""
    from app.models.database import create_session_local
    
    # Configure logging for this background task
    logger = logging.getLogger(__name__)

    session_local = None
    engine = None
    try:
        # Create a new database session for the background task
        session_local, engine = create_session_local()
        async with session_local() as db:
            try:
                logger.info(f"process_document_background called with file_path={file_path}, upload_id={upload_id}")
                # Process the document using the embedding service
                document_id, chunks_created = await embedding_service.process_uploaded_document(
                    db=db,
                    file_path=file_path,
                    original_filename=original_filename,
                    file_type=file_type,
                )
                
                # Store success status (you could store this in Redis or a status table)
                logger.info(f"Successfully processed document: {document_id}, created {chunks_created} chunks")
                
            except Exception as e:
                # Log the error but do not re-raise to prevent worker crash
                logger.error(f"Failed to process document {original_filename} (upload_id: {upload_id}): {str(e)}", exc_info=True)
                # Clean up file if processing failed
                if Path(file_path).exists():
                    Path(file_path).unlink()
            finally:
                # Make sure to dispose of the engine if it was created
                if engine:
                    await engine.dispose()
            
    except Exception as e:
        # Catch exceptions during session creation or engine disposal
        logger.error(f"Critical error in process_document_background for {original_filename} (upload_id: {upload_id}): {str(e)}", exc_info=True)
        # Clean up file if processing failed
        if Path(file_path).exists():
            Path(file_path).unlink()


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


@router.post("/documents/upload-multiple")
async def upload_multiple_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload multiple document files and process them asynchronously in the background"""
    
    # Validate file types and sizes
    allowed_types = {
        'application/pdf': '.pdf',
        'text/plain': '.txt',
        'text/markdown': '.md',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
    }
    
    max_size = 50 * 1024 * 1024  # 50MB per file
    upload_results = []
    
    for file in files:
        # Validate file type
        if file.content_type not in allowed_types:
            upload_results.append({
                "filename": file.filename,
                "status": "failed",
                "error": f"Unsupported file type: {file.content_type}"
            })
            continue
        
        # Validate file size
        if file.size and file.size > max_size:
            upload_results.append({
                "filename": file.filename,
                "status": "failed",
                "error": "File too large. Maximum size is 50MB"
            })
            continue
        
        try:
            # Create uploads directory if it doesn't exist
            upload_dir = Path("/app/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename and upload ID
            file_extension = allowed_types[file.content_type]
            upload_id = str(uuid4())
            unique_filename = f"{upload_id}{file_extension}"
            file_path = upload_dir / unique_filename
            
            # Save file to disk
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
            
            upload_results.append({
                "filename": file.filename,
                "upload_id": upload_id,
                "status": "processing"
            })
            
        except Exception as e:
            upload_results.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })
    
    # Count successful uploads
    successful_uploads = [r for r in upload_results if r["status"] == "processing"]
    
    return {
        "message": f"Uploaded {len(successful_uploads)} of {len(files)} files",
        "uploads": upload_results
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document and all its chunks from the database"""
    from sqlalchemy import select
    from app.models.chat import Document
    
    try:
        # Find the document
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete the document (this will cascade delete chunks due to foreign key relationship)
        await db.delete(document)
        await db.commit()
        
        return {
            "message": f"Document '{document.title}' deleted successfully",
            "document_id": str(document_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.get("/documents/search")
async def search_documents_by_name(
    query: str = "",
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Search documents by title for autocomplete functionality"""
    from sqlalchemy import select, func, or_
    from app.models.chat import Document, DocumentChunk
    
    try:
        # Build the base query with chunk count
        stmt = select(
            Document,
            func.count(DocumentChunk.id).label('chunk_count')
        ).outerjoin(
            DocumentChunk, Document.id == DocumentChunk.document_id
        ).group_by(Document.id)
        
        # Add search filters if query is provided
        if query.strip():
            search_term = f"%{query.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Document.title).like(search_term),
                    func.lower(Document.filename).like(search_term)
                )
            )
        
        # Order by relevance (exact matches first, then partial matches)
        # Then by creation date (newest first)
        if query.strip():
            stmt = stmt.order_by(
                # Exact title matches first
                func.lower(Document.title) == query.lower(),
                # Titles starting with query second  
                func.lower(Document.title).like(f"{query.lower()}%"),
                # Then by creation date
                Document.created_at.desc()
            )
        else:
            stmt = stmt.order_by(Document.created_at.desc())
        
        # Apply limit
        stmt = stmt.limit(limit)
        
        result = await db.execute(stmt)
        documents_with_counts = result.all()
        
        return {
            "query": query,
            "documents": [
                {
                    "id": str(doc.id),
                    "title": doc.title,
                    "source_type": doc.source_type,
                    "source_id": doc.source_id,
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                    "chunk_count": chunk_count,
                    "metadata": json.loads(doc.document_metadata) if doc.document_metadata else {}
                }
                for doc, chunk_count in documents_with_counts
            ],
            "total_results": len(documents_with_counts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search documents: {str(e)}")


@router.get("/documents/{document_id}/pdf")
async def serve_pdf_file(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Serve the original PDF file for a document if it exists"""
    from sqlalchemy import select
    from app.models.chat import Document
    
    try:
        # Find the document
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if it's a PDF
        if document.file_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Document is not a PDF")
        
        # Get file path from metadata
        if document.document_metadata:
            metadata = json.loads(document.document_metadata)
            file_path = metadata.get("file_path")
            
            if file_path and os.path.exists(file_path):
                return FileResponse(
                    file_path,
                    media_type="application/pdf",
                    filename=document.filename or f"document_{document_id}.pdf",
                    headers={
                        "Content-Disposition": f'inline; filename="{document.filename or f"document_{document_id}.pdf"}"'
                    }
                )
        
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve PDF: {str(e)}")


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific message from a chat"""
    from sqlalchemy import select
    from app.models.chat import Message
    
    try:
        # Find the message - need to join with chat to verify user ownership
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(Message)
            .options(selectinload(Message.chat))
            .where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()
        
        # Verify the user owns the chat that contains this message
        # No user ownership check needed anymore
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Store chat_id for response
        chat_id = message.chat_id
        
        # Delete the message
        await db.delete(message)
        await db.commit()
        
        return {
            "message": "Message deleted successfully",
            "message_id": str(message_id),
            "chat_id": str(chat_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete message: {str(e)}")


@router.post("/chats/{chat_id}/summarize")
async def summarize_chat(
    chat_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Generate an auto-summary of a chat conversation"""
    try:
        # Get the chat with all messages
        chat = await ChatService.get_chat(db, chat_id, None)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        if not chat.messages:
            raise HTTPException(status_code=400, detail="Chat has no messages to summarize")
        
        # Build conversation text
        conversation_text = ""
        for msg in sorted(chat.messages, key=lambda x: x.created_at):
            role = "User" if msg.role == "user" else "Assistant"
            conversation_text += f"{role}: {msg.content}\n\n"
        
        # Create summarization prompt
        summary_prompt = f"""Please provide a concise, informative summary of the following conversation. The summary should:
1. Capture the main topics discussed
2. Highlight key insights, solutions, or conclusions
3. Be suitable as a title and description for a knowledge base document
4. Be 2-3 sentences long

Conversation:
{conversation_text}

Please respond with just the summary, no additional formatting."""
        
        # Generate summary using the AI service
        from app.services.azure_openai import azure_openai_service
        messages = [
            {"role": "system", "content": "You are a helpful assistant that creates concise, informative summaries of conversations."},
            {"role": "user", "content": summary_prompt}
        ]
        
        summary = ""
        async for chunk in azure_openai_service.generate_chat_completion(messages):
            summary += chunk
        
        return {
            "summary": summary.strip(),
            "chat_id": str(chat_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to summarize chat: {str(e)}")


@router.get("/messages/{message_id}/status")
async def get_message_status(
    message_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get deep research status for a specific message"""
    status = await ChatService.get_message_status(db, message_id, None)
    
    if not status:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return status
