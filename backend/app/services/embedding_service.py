"""
Embedding service using Azure OpenAI directly
"""
from typing import List, Optional, Tuple
from openai import AzureOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader
import tiktoken
import json
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.config import settings
from app.models.chat import Chat, Message, Document, DocumentChunk


class EmbeddingService:
    def __init__(self):
        # Initialize Azure OpenAI client directly
        self.client = AzureOpenAI(
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key
        )
        
        # Initialize text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Characters per chunk
            chunk_overlap=200,  # Overlap between chunks
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize tokenizer for counting tokens
        self.tokenizer = tiktoken.encoding_for_model(settings.azure_openai_embedding_deployment_name)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        return len(self.tokenizer.encode(text))
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        response = self.client.embeddings.create(
            input=[text],
            model=settings.azure_openai_embedding_deployment_name
        )
        return response.data[0].embedding
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        response = self.client.embeddings.create(
            input=texts,
            model=settings.azure_openai_embedding_deployment_name
        )
        return [item.embedding for item in response.data]
    
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
        source_types: List[str] = None
    ) -> List[DocumentChunk]:
        """
        Perform similarity search against all document chunks (unified search).
        """
        from sqlalchemy import select, func
        from sqlalchemy.orm import selectinload, joinedload
        from app.models.chat import DocumentChunk, Document
        
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
        
        # Add source type filtering if specified
        if source_types:
            stmt = stmt.where(Document.source_type.in_(source_types))
        
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
        file_type: str
    ) -> Tuple[UUID, int]:
        """Process an uploaded document file and store it in the knowledge base"""
        from sqlalchemy import select
        
        # Load document based on file type
        documents = await self._load_document(file_path, file_type)
        
        if not documents:
            raise ValueError("Could not extract content from the document")
        
        # Combine all document content
        full_content = "\n\n".join([doc.page_content for doc in documents])
        
        # Create document record
        document_id = uuid4()
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
                "file_size": Path(file_path).stat().st_size if Path(file_path).exists() else None
            })
        )
        
        db.add(document)
        await db.flush()  # Get the document ID
        
        # Chunk the content
        chunks = self.text_splitter.split_text(full_content)
        
        # Process chunks and create embeddings
        chunk_objects = []
        for i, chunk_content in enumerate(chunks):
            # Generate embedding for this chunk
            embedding = self.embed_text(chunk_content)
            token_count = self.count_tokens(chunk_content)
            
            # Create chunk object
            chunk = DocumentChunk(
                id=uuid4(),
                document_id=document_id,
                content=chunk_content,
                chunk_index=i,
                token_count=token_count,
                embedding=embedding
            )
            chunk_objects.append(chunk)
        
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
