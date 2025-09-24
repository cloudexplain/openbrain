"""
Embedding service supporting both Azure OpenAI and Ollama
"""
from typing import List, Optional, Tuple
from openai import AzureOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader
import tiktoken
import json
import logging
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.config import get_settings
from app.models.chat import Chat, Message, Document, DocumentChunk

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        settings = get_settings()
        # Detect provider based on configuration
        provider = (settings.llm_provider or "azure_openai").lower()
        self.provider = provider

        # Initialize appropriate embedding client
        if provider == "ollama":
            # Use Ollama for embeddings
            from app.services.langchain import langchain_ollama_service
            self.ollama_service = langchain_ollama_service
            self.client = None
            self.tokenizer = None
            logger.info("Using Ollama for embeddings")
        else:
            # Use Azure OpenAI for embeddings (default)
            try:
                self.client = AzureOpenAI(
                    api_version=settings.azure_openai_api_version,
                    azure_endpoint=settings.azure_openai_endpoint,
                    api_key=settings.azure_openai_api_key
                )
                # Initialize tokenizer for counting tokens
                self.tokenizer = tiktoken.encoding_for_model(settings.azure_openai_embedding_deployment_name)
                self.ollama_service = None
                logger.info("Using Azure OpenAI for embeddings")
            except Exception as e:
                logger.error("Failed to initialize Azure OpenAI client: %s", e)
                # Fallback to Ollama if Azure fails
                from app.services.langchain import langchain_ollama_service
                self.ollama_service = langchain_ollama_service
                self.client = None
                self.tokenizer = None
                self.provider = "ollama"
                logger.info("Fallback to Ollama for embeddings")
        
        # Initialize text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Characters per chunk
            chunk_overlap=200,  # Overlap between chunks
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Simple approximation for Ollama
            return max(1, len(text) // 4)
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if self.provider == "ollama" and self.ollama_service:
            return self.ollama_service.embed(text)
        elif self.client:
            settings = get_settings()
            response = self.client.embeddings.create(
                input=[text],
                model=settings.azure_openai_embedding_deployment_name
            )
            return response.data[0].embedding
        else:
            raise RuntimeError("No embedding service available")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self.provider == "ollama" and self.ollama_service:
            # Ollama doesn't have batch embedding, so we embed one by one
            return [self.ollama_service.embed(text) for text in texts]
        elif self.client:
            settings = get_settings()
            response = self.client.embeddings.create(
                input=texts,
                model=settings.azure_openai_embedding_deployment_name
            )
            return [item.embedding for item in response.data]
        else:
            raise RuntimeError("No embedding service available")
    
    def chunk_chat_conversation(self, chat: Chat) -> List[Tuple[str, List[UUID], dict]]:
        """
        Chunk a chat conversation into meaningful segments.
        Returns list of (content, message_ids, metadata) tuples.
        """
        if not chat.messages:
            return []
        
        # Sort messages by creation time
        sorted_messages = sorted(chat.messages, key=lambda x: x.created_at)
        
        # Build conversation text with message boundaries
        conversation_parts = []
        message_boundaries = []
        current_pos = 0
        
        for msg in sorted_messages:
            role_prefix = f"\n\n{msg.role.upper()}:\n"
            content = msg.content
            full_text = f"{role_prefix}{content}"
            
            conversation_parts.append(full_text)
            message_boundaries.append({
                'message_id': msg.id,
                'start': current_pos,
                'end': current_pos + len(full_text),
                'role': msg.role
            })
            current_pos += len(full_text)
        
        full_conversation = "".join(conversation_parts)
        
        # Split into chunks using LangChain
        documents = [LangChainDocument(
            page_content=full_conversation,
            metadata={
                'chat_id': str(chat.id),
                'chat_title': chat.title,
                'total_messages': len(sorted_messages)
            }
        )]
        
        chunks = self.text_splitter.split_documents(documents)
        
        # Map chunks back to original messages
        result_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_content = chunk.page_content
            
            # Find which messages this chunk spans
            chunk_start = full_conversation.find(chunk_content)
            chunk_end = chunk_start + len(chunk_content)
            
            chunk_message_ids = []
            for boundary in message_boundaries:
                # Check if message overlaps with chunk
                if (boundary['start'] < chunk_end and boundary['end'] > chunk_start):
                    chunk_message_ids.append(boundary['message_id'])
            
            # Create metadata
            metadata = {
                'chunk_index': i,
                'chat_title': chat.title,
                'message_count': len(chunk_message_ids),
                'chunk_start': chunk_start,
                'chunk_end': chunk_end,
                'created_at': chat.created_at.isoformat() if chat.created_at else None
            }
            
            result_chunks.append((chunk_content, chunk_message_ids, metadata))
        
        return result_chunks
    
    def process_chat_for_knowledge(
        self, 
        db: AsyncSession, 
        chat: Chat
    ) -> Tuple[Document, List[DocumentChunk]]:
        """
        Process a chat conversation into a Document with DocumentChunk embeddings.
        Returns (Document, List[DocumentChunk]) (not yet committed to DB).
        """
        chunks = self.chunk_chat_conversation(chat)
        if not chunks:
            return None, []
        
        # Create Document for this chat
        chat_document = Document(
            title=f"Chat: {chat.title}",
            source_type="chat",
            source_id=str(chat.id),
            document_metadata=json.dumps({
                "chat_id": str(chat.id),
                "chat_title": chat.title,
                "message_count": len(chat.messages),
                "created_at": chat.created_at.isoformat() if chat.created_at else None
            })
        )
        
        # Extract content for batch embedding
        chunk_contents = [chunk[0] for chunk in chunks]
        
        # Generate embeddings for all chunks at once
        embeddings = self.embed_texts(chunk_contents)
        
        # Create DocumentChunk objects
        document_chunks = []
        for i, ((content, message_ids, metadata), embedding) in enumerate(zip(chunks, embeddings)):
            token_count = self.count_tokens(content)
            
            # Enhanced metadata for chat chunks
            chunk_metadata = {
                **metadata,
                "message_ids": [str(mid) for mid in message_ids],
                "source_type": "chat",
                "chat_id": str(chat.id)
            }
            
            document_chunk = DocumentChunk(
                content=content,
                chunk_index=i,
                token_count=token_count,
                embedding=embedding,
                chunk_metadata=json.dumps(chunk_metadata),
                summary=None  # Could add summarization later
            )
            
            document_chunks.append(document_chunk)
        
        return chat_document, document_chunks
    
    async def similarity_search(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
        source_types: List[str] = None,
        tag_ids: List[UUID] = None,
        document_ids: List[UUID] = None
    ) -> List[DocumentChunk]:
        """
        Perform similarity search against all document chunks (unified search).
        """
        from sqlalchemy import select, func
        from sqlalchemy.orm import selectinload, joinedload
        from app.models.chat import DocumentChunk, Document, DocumentTag
        
        # Generate embedding for the query
        query_embedding = self.embed_text(query)
        
        # First, try to find documents within the similarity threshold
        stmt = (
            select(
                DocumentChunk,
                Document.title.label('document_title'),
                Document.source_type,
                Document.source_id,
                DocumentChunk.embedding.cosine_distance(query_embedding).label('distance')
            )
            .join(Document)
            .where(
                DocumentChunk.embedding.cosine_distance(query_embedding) < (1.0 - similarity_threshold)
            )
        )
        
        # User filtering removed - no longer needed
        
        # Add source type filtering if specified
        if source_types:
            stmt = stmt.where(Document.source_type.in_(source_types))
        
        # Add tag filtering if specified
        if tag_ids:
            stmt = stmt.join(
                DocumentTag, Document.id == DocumentTag.document_id
            ).where(
                DocumentTag.tag_id.in_(tag_ids)
            )
        
        # Add document filtering if specified
        if document_ids:
            stmt = stmt.where(Document.id.in_(document_ids))
        
        # Order by distance and limit
        stmt = stmt.order_by('distance').limit(limit)
        
        # Execute query
        result = await db.execute(stmt)
        rows = result.all()
        
        # If no documents found within threshold, get the top 3 closest documents
        if not rows:
            fallback_stmt = (
                select(
                    DocumentChunk,
                    Document.title.label('document_title'),
                    Document.source_type,
                    Document.source_id,
                    DocumentChunk.embedding.cosine_distance(query_embedding).label('distance')
                )
                .join(Document)
            )
            
            # Add source type filtering if specified
            if source_types:
                fallback_stmt = fallback_stmt.where(Document.source_type.in_(source_types))
            
            # Add tag filtering if specified for fallback too
            if tag_ids:
                fallback_stmt = fallback_stmt.join(
                    DocumentTag, Document.id == DocumentTag.document_id
                ).where(
                    DocumentTag.tag_id.in_(tag_ids)
                )
            
            # Add document filtering if specified for fallback too
            if document_ids:
                fallback_stmt = fallback_stmt.where(Document.id.in_(document_ids))
            
            # Order by distance and get top 3
            fallback_stmt = fallback_stmt.order_by('distance').limit(3)
            
            # Execute fallback query
            result = await db.execute(fallback_stmt)
            rows = result.all()
        
        # Convert results to DocumentChunk objects with additional metadata
        chunks = []
        for row in rows:
            chunk = row.DocumentChunk
            
            # Add search context as attributes
            chunk.search_distance = row.distance
            chunk.document_title = row.document_title
            chunk.source_type = row.source_type
            chunk.source_id = row.source_id
            
            chunks.append(chunk)
        
        return chunks
    
    async def process_uploaded_document(
        self,
        db: AsyncSession,
        file_path: str,
        original_filename: str,
        file_type: str,
    ) -> Tuple[UUID, int]:
        """Process an uploaded document file and store it in the knowledge base"""
        from sqlalchemy import select
        
        # Load document based on file type
        documents = await self._load_document(file_path, file_type)
        
        if not documents:
            raise ValueError("Could not extract content from the document")
        
        # Create document record
        document_id = uuid4()

        # No user management for uploaded files
        document = Document(
            id=document_id,
            title=original_filename or f"Uploaded Document {document_id}",
            source_type="file",
            source_id=str(document_id),
            filename=original_filename,
            file_type=file_type,
            document_metadata=json.dumps({
                "file_path": file_path,
                "original_filename": original_filename,
                "file_type": file_type,
                "file_size": Path(file_path).stat().st_size if Path(file_path).exists() else None,
                "total_pages": len(documents) if file_type == "application/pdf" else None
            })
        )
        
        db.add(document)
        await db.flush()  # Get the document ID
        
        # Process each page/document separately to maintain page information
        chunk_objects = []
        global_chunk_index = 0
        
        for doc_idx, doc in enumerate(documents):
            # Extract page number from metadata (PyPDFLoader provides this)
            page_num = doc.metadata.get('page', doc_idx) if hasattr(doc, 'metadata') else doc_idx
            
            # Split this page/document into chunks
            page_chunks = self.text_splitter.split_text(doc.page_content)
            
            for local_chunk_idx, chunk_content in enumerate(page_chunks):
                # Generate embedding for this chunk
                embedding = self.embed_text(chunk_content)
                token_count = self.count_tokens(chunk_content)
                
                # Enhanced metadata for PDF chunks
                chunk_metadata = {
                    "page_number": page_num + 1,  # Convert to 1-based indexing for display
                    "page_index": page_num,  # Keep 0-based for processing
                    "chunk_on_page": local_chunk_idx,
                    "total_chunks_on_page": len(page_chunks)
                }
                
                # For PDFs, try to get more specific location info
                if file_type == "application/pdf":
                    # Find position of chunk within the page
                    page_text = doc.page_content
                    chunk_start = page_text.find(chunk_content)
                    chunk_end = chunk_start + len(chunk_content) if chunk_start != -1 else -1
                    
                    chunk_metadata.update({
                        "chunk_start_char": chunk_start,
                        "chunk_end_char": chunk_end,
                        "page_char_count": len(page_text)
                    })
                
                # Create chunk object
                chunk = DocumentChunk(
                    id=uuid4(),
                    document_id=document_id,
                    content=chunk_content,
                    chunk_index=global_chunk_index,
                    token_count=token_count,
                    embedding=embedding,
                    chunk_metadata=json.dumps(chunk_metadata)
                )
                chunk_objects.append(chunk)
                global_chunk_index += 1
        
        # Add all chunks to database
        db.add_all(chunk_objects)
        
        # Commit the transaction
        await db.commit()
        
        return document_id, len(chunk_objects)
    
    async def _load_document(self, file_path: str, file_type: str) -> List[LangChainDocument]:
        """Load document using appropriate LangChain loader based on file type"""
        
        if file_type == "application/pdf":
            loader = PyPDFLoader(file_path)
            return await self._async_load(loader)
        elif file_type in ["text/plain", "text/markdown"]:
            loader = TextLoader(file_path)
            return await self._async_load(loader)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            loader = UnstructuredWordDocumentLoader(file_path)
            return await self._async_load(loader)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    async def _async_load(self, loader) -> List[LangChainDocument]:
        """Async wrapper for document loader"""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, loader.load)


# Global instance
embedding_service = EmbeddingService()
