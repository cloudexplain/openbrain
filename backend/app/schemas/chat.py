from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID
from pydantic import ConfigDict, BaseModel, Field, field_serializer


class MessageBase(BaseModel):
    content: str
    role: str


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    id: UUID
    chat_id: UUID
    created_at: datetime
    token_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('id', 'chat_id')
    def serialize_uuid(self, value: UUID) -> str:
        return str(value)


class ChatBase(BaseModel):
    title: str


class ChatCreate(ChatBase):
    pass


class ChatUpdate(BaseModel):
    title: Optional[str] = None


class Chat(ChatBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = []
    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('id')
    def serialize_uuid(self, value: UUID) -> str:
        return str(value)


class ChatListItem(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None
    message_count: int = 0
    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('id')
    def serialize_uuid(self, value: UUID) -> str:
        return str(value)


class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[UUID] = None
    use_rag: bool = True  # Enable RAG by default
    rag_limit: int = 5  # Number of relevant chunks to retrieve
    rag_threshold: float = 0.7  # Minimum similarity threshold


class StreamResponse(BaseModel):
    type: str  # 'content', 'done', 'error'
    content: Optional[str] = None
    message_id: Optional[UUID] = None
    chat_id: Optional[UUID] = None
    error: Optional[str] = None