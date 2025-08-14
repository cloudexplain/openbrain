from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from .database import Base


class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False)
    content = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # For RAG support - store token count and embeddings
    token_count = Column(Integer, nullable=True)
    embedding = Column(Vector(1536), nullable=True)  # OpenAI text-embedding-ada-002 dimension
    
    # Relationship to chat
    chat = relationship("Chat", back_populates="messages")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # 'chat', 'file', 'url', etc.
    source_id = Column(String(255), nullable=True)  # chat_id, file_path, url, etc.
    
    # For file uploads
    filename = Column(String(255), nullable=True)  # Only for file source_type
    file_type = Column(String(50), nullable=True)   # Only for file source_type  
    file_size = Column(Integer, nullable=True)      # Only for file source_type
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Document metadata (JSON)
    document_metadata = Column(Text, nullable=True)  # JSON string for source-specific metadata
    
    # Relationship to chunks
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    token_count = Column(Integer, nullable=False)
    
    # Vector embedding for semantic search
    embedding = Column(Vector(1536), nullable=False)  # OpenAI text-embedding-ada-002 dimension
    
    # Chunk metadata (JSON) - can store message_ids for chats, page_num for PDFs, etc.
    chunk_metadata = Column(Text, nullable=True)  # JSON string for chunk-specific metadata
    
    # Optional summary for this chunk
    summary = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to document
    document = relationship("Document", back_populates="chunks")


# Chat model now uses Documents for knowledge storage via source_type='chat'