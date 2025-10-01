from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from .base import Base


class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chats")
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
    
    # Store citation mappings and document references as JSON
    citation_mapping = Column(Text, nullable=True)  # JSON string for inline citation data
    document_references = Column(Text, nullable=True)  # JSON string for document references
    
    # Deep research fields
    is_deep_research = Column(Boolean, default=False, nullable=False)
    deep_research_status = Column(String(20), default=None, nullable=True)  # 'pending', 'running', 'completed', 'failed'
    deep_research_params = Column(Text, nullable=True)  # JSON string for deep research parameters
    deep_research_error = Column(Text, nullable=True)  # Error message if research failed
    
    # Relationship to chat
    chat = relationship("Chat", back_populates="messages")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default='#4F46E5', nullable=False)  # Default indigo color
    parent_id = Column(UUID(as_uuid=True), ForeignKey("folders.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="folders")
    parent = relationship("Folder", remote_side=[id], back_populates="children")
    children = relationship("Folder", back_populates="parent", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="folder")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id"), nullable=True)
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

    # Relationships
    user = relationship("User", back_populates="documents")
    folder = relationship("Folder", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    # Relationship to tags through junction table
    tags = relationship("Tag", secondary="document_tags", back_populates="documents")


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


class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default='#808080')  # Hex color for UI
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="tags")
    documents = relationship("Document", secondary="document_tags", back_populates="tags")


class DocumentTag(Base):
    __tablename__ = "document_tags"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())