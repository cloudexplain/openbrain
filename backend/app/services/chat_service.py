from typing import List, Optional, AsyncGenerator
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import text
import json

from app.models.chat import Chat as ChatModel, Message as MessageModel
from app.schemas.chat import ChatCreate, MessageCreate, ChatListItem, Chat, Message
from app.services.azure_openai import azure_openai_service
from app.services.embedding_service import embedding_service


class ChatService:
    @staticmethod
    def strip_system_context_tags(content: str) -> str:
        """Remove system context tags from content for frontend display"""
        import re
        # Remove <system_context>...</system_context> tags and their content
        pattern = r'<system_context>.*?</system_context>\s*\n*'
        return re.sub(pattern, '', content, flags=re.DOTALL).strip()
    @staticmethod
    async def create_chat(db: AsyncSession, chat_data: ChatCreate) -> Chat:
        """Create a new chat"""
        db_chat = ChatModel(title=chat_data.title)
        db.add(db_chat)
        await db.commit()
        await db.refresh(db_chat)
        return db_chat
    
    @staticmethod
    async def get_chat(db: AsyncSession, chat_id: UUID) -> Optional[Chat]:
        """Get a chat by ID with messages"""
        result = await db.execute(
            select(ChatModel)
            .options(selectinload(ChatModel.messages))
            .where(ChatModel.id == chat_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_chats(db: AsyncSession, limit: int = 50) -> List[ChatListItem]:
        """Get all chats with basic info"""
        # Get chats with their latest message
        query = """
        SELECT 
            c.id,
            c.title,
            c.created_at,
            c.updated_at,
            (
                SELECT m.content 
                FROM messages m 
                WHERE m.chat_id = c.id 
                ORDER BY m.created_at DESC 
                LIMIT 1
            ) as last_message,
            (
                SELECT COUNT(*) 
                FROM messages m 
                WHERE m.chat_id = c.id
            ) as message_count
        FROM chats c
        ORDER BY c.updated_at DESC
        LIMIT :limit
        """
        
        result = await db.execute(text(query), {"limit": limit})
        rows = result.fetchall()
        
        return [
            ChatListItem(
                id=row.id,
                title=row.title,
                created_at=row.created_at,
                updated_at=row.updated_at,
                last_message=row.last_message,
                message_count=row.message_count
            )
            for row in rows
        ]
    
    @staticmethod
    async def delete_chat(db: AsyncSession, chat_id: UUID) -> bool:
        """Delete a chat and all its messages"""
        result = await db.execute(select(ChatModel).where(ChatModel.id == chat_id))
        chat = result.scalar_one_or_none()
        
        if chat:
            await db.delete(chat)
            await db.commit()
            return True
        return False
    
    @staticmethod
    async def add_message(
        db: AsyncSession, 
        chat_id: UUID, 
        message_data: MessageCreate
    ) -> Message:
        """Add a message to a chat"""
        # Count tokens
        token_count = azure_openai_service.count_tokens(message_data.content)
        
        db_message = MessageModel(
            chat_id=chat_id,
            content=message_data.content,
            role=message_data.role,
            token_count=token_count
        )
        
        db.add(db_message)
        await db.commit()
        await db.refresh(db_message)
        
        # Update chat's updated_at timestamp
        await db.execute(
            select(ChatModel).where(ChatModel.id == chat_id)
        )
        chat_result = await db.execute(select(ChatModel).where(ChatModel.id == chat_id))
        chat = chat_result.scalar_one_or_none()
        if chat:
            await db.commit()  # This will trigger the onupdate for updated_at
        
        return db_message
    
    @staticmethod
    async def generate_response(
        db: AsyncSession,
        chat_id: UUID,
        user_message: str,
        use_rag: bool = True,
        rag_limit: int = 5,
        rag_threshold: float = 0.7
    ) -> AsyncGenerator[tuple[str, Optional[UUID]], None]:
        """Generate AI response for a chat message with optional RAG support"""
        # Get chat with messages for context
        chat = await ChatService.get_chat(db, chat_id)
        if not chat:
            raise ValueError("Chat not found")
        
        # Add user message (store original without system context tags)
        user_msg = await ChatService.add_message(
            db, 
            chat_id, 
            MessageCreate(content=user_message, role="user")
        )
        
        # Perform similarity search to retrieve relevant context if RAG is enabled
        relevant_chunks = []
        if use_rag:
            relevant_chunks = await embedding_service.similarity_search(
                db=db,
                query=user_message,
                limit=rag_limit,
                similarity_threshold=rag_threshold
            )
            print(f"\nTHESE ARE THE RELEVANT CHUNKS: {relevant_chunks}!")
        
        # Build context from retrieved chunks
        context_parts = []
        if relevant_chunks:
            # Check if we're using fallback results (all chunks have distance > threshold)
            threshold_distance = 1.0 - rag_threshold
            using_fallback = all(getattr(chunk, 'search_distance', 0) >= threshold_distance for chunk in relevant_chunks)
            
            if using_fallback:
                context_parts.append("## Related Knowledge from Database (Less Relevant):\n")
                context_parts.append("*Note: No highly relevant matches found. The following are the closest available documents:*\n\n")
            else:
                context_parts.append("## Relevant Knowledge from Database:\n")
            
            for i, chunk in enumerate(relevant_chunks, 1):
                # Parse metadata to get source information
                metadata = json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {}
                source_info = f"[Source: {getattr(chunk, 'document_title', 'Unknown')}]"
                distance = getattr(chunk, 'search_distance', 'unknown')
                
                if isinstance(distance, float):
                    confidence = f" (Similarity: {(1.0 - distance) * 100:.1f}%)"
                else:
                    confidence = ""
                
                context_parts.append(f"{i}. {source_info}{confidence}\n{chunk.content}\n")
            
            context_parts.append("\n---\n\n")
        
        # Build conversation history for OpenAI
        messages = []
        
        # Check if the model supports system messages (o1-mini and o1-preview do not)
        model_name = azure_openai_service.deployment_name.lower()
        supports_system_messages = not any(unsupported in model_name for unsupported in ['o1-mini', 'o1-preview', 'o1'])
        
        # Initialize hidden_context for o1-mini models
        hidden_context = ""
        
        # Add system message or convert to user message with hidden tags
        if context_parts:
            # Check if we're using fallback results
            if using_fallback:
                context_message = (
                    "You are a helpful assistant with access to a knowledge base. "
                    "The following context was retrieved but may not be highly relevant to the user's question. "
                    "Use the context cautiously and only if it actually helps answer the question. "
                    "Feel free to indicate when the available information is limited or not directly applicable.\n\n"
                    + "".join(context_parts)
                )
            else:
                context_message = (
                    "You are a helpful assistant with access to a knowledge base. "
                    "Use the following retrieved context to answer the user's questions. "
                    "If the context is relevant, incorporate it into your response. "
                    "If the context is not relevant, you can ignore it.\n\n"
                    + "".join(context_parts)
                )
            
            if supports_system_messages:
                messages.append({"role": "system", "content": context_message})
            else:
                # For o1-mini and similar models, prepare hidden context
                hidden_context = f"<system_context>\n{context_message}</system_context>\n\n"
        
        # Add conversation history (excluding the message we just added)
        for msg in sorted(chat.messages[:-1], key=lambda x: x.created_at):
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add the current user message (with hidden context for o1-mini if needed)
        if hidden_context:
            # Prepend hidden context to user message for o1-mini
            final_user_message = f"{hidden_context}{user_message}"
        else:
            final_user_message = user_message
            
        messages.append({"role": "user", "content": final_user_message})
        
        # Generate response
        response_content = ""
        async for chunk in azure_openai_service.generate_chat_completion(messages):
            response_content += chunk
            yield chunk, None
        
        # Save assistant response
        assistant_msg = await ChatService.add_message(
            db,
            chat_id,
            MessageCreate(content=response_content, role="assistant")
        )
        
        # Yield final message ID
        yield "", assistant_msg.id
    
    @staticmethod
    async def get_or_create_chat(db: AsyncSession, chat_id: Optional[UUID] = None, title: str = "New Chat") -> Chat:
        """Get existing chat or create new one"""
        if chat_id:
            chat = await ChatService.get_chat(db, chat_id)
            if chat:
                return chat
        
        # Create new chat
        return await ChatService.create_chat(db, ChatCreate(title=title))
