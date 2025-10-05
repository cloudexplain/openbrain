from typing import List, Optional, AsyncGenerator, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import text
import json
import re
import asyncio
from datetime import datetime
import logging
import inspect

from app.models.chat import Chat as ChatModel, Message as MessageModel, Tag, DocumentTag
from app.schemas.chat import ChatCreate, MessageCreate, ChatListItem, Chat, Message
from app.services.llm_factory import llm_service
from app.services.embedding_service import embedding_service
from app.services.deep_research_service import DeepResearchService


class ChatService:
    @staticmethod
    def strip_system_context_tags(content: str) -> str:
        """Remove system context tags from content for frontend display"""
        import re
        # Remove <system_context>...</system_context> tags and their content
        pattern = r'<system_context>.*?</system_context>\s*\n*'
        return re.sub(pattern, '', content, flags=re.DOTALL).strip()
    
    @staticmethod
    def extract_tags_from_message(message: str) -> Set[str]:
        """Extract tag references from a message (e.g., #tagname or [tag:tagname])"""
        tags = set()
        
        # Pattern 1: #tagname (alphanumeric and underscore, dash)
        hashtag_pattern = r'#([\w-]+)'
        tags.update(re.findall(hashtag_pattern, message))
        
        # Pattern 2: [tag:tagname]
        bracket_pattern = r'\[tag:([\w-]+)\]'
        tags.update(re.findall(bracket_pattern, message))
        
        return tags
    
    @staticmethod
    def extract_document_references_from_message(message: str) -> Set[str]:
        """Extract document references from a message (e.g., /doc "Document Name" or /doc DocumentName)"""
        documents = set()
        
        # Pattern 1: /doc "Document Name" or /document "Document Name"
        quoted_pattern = r'/(?:doc|document)\s+"([^"]+)"'
        documents.update(re.findall(quoted_pattern, message))
        
        # Pattern 2: /doc DocumentName or /document DocumentName (single word)
        unquoted_pattern = r'/(?:doc|document)\s+([^\s]+)'
        unquoted_matches = re.findall(unquoted_pattern, message)
        # Filter out matches that are already quoted (to avoid duplicates)
        for match in unquoted_matches:
            if not match.startswith('"'):
                documents.add(match)
        
        return documents
    
    @staticmethod
    async def get_tag_ids_by_names(db: AsyncSession, tag_names: Set[str]) -> List[UUID]:
        """Get tag IDs from tag names"""
        if not tag_names:
            return []

        # Convert to lowercase for case-insensitive matching
        lower_names = [name.lower() for name in tag_names]

        result = await db.execute(
            select(Tag.id).where(
                Tag.name.in_(tag_names) |
                Tag.name.in_(lower_names)
            )
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_document_ids_by_titles(db: AsyncSession, document_titles: Set[str]) -> List[UUID]:
        """Get document IDs from document titles"""
        if not document_titles:
            return []

        from app.models.chat import Document
        from sqlalchemy import func, or_

        # Build conditions for case-insensitive matching on both title and filename
        conditions = []
        for title in document_titles:
            conditions.extend([
                func.lower(Document.title) == title.lower(),
                func.lower(Document.filename) == title.lower()
            ])

        result = await db.execute(
            select(Document.id).where(
                or_(*conditions)
            )
        )
        return list(result.scalars().all())
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
    async def update_chat(db: AsyncSession, chat_id: UUID, chat_data) -> Optional[Chat]:
        """Update a chat's title and/or messages"""
        # Get the chat
        result = await db.execute(
            select(ChatModel)
            .options(selectinload(ChatModel.messages))
            .where(ChatModel.id == chat_id)
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            return None
        
        # Update title if provided
        if chat_data.title is not None:
            chat.title = chat_data.title
        
        # Update messages if provided
        if chat_data.messages is not None:
            # Delete existing messages
            await db.execute(
                text("DELETE FROM messages WHERE chat_id = :chat_id"),
                {"chat_id": str(chat_id)}
            )
            
            # Add new messages
            for idx, msg_data in enumerate(chat_data.messages):
                message = MessageModel(
                    chat_id=chat_id,
                    content=msg_data.get('content', ''),
                    role=msg_data.get('role', 'user'),
                    token_count=len(msg_data.get('content', '').split())  # Simple token count
                )
                db.add(message)
        
        await db.commit()
        await db.refresh(chat)
        
        # Return the updated chat with messages
        return Chat(
            id=chat.id,
            title=chat.title,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            messages=[
                Message(
                    id=msg.id,
                    chat_id=msg.chat_id,
                    content=ChatService.strip_system_context_tags(msg.content),
                    role=msg.role,
                    created_at=msg.created_at,
                    token_count=msg.token_count
                )
                for msg in chat.messages
            ]
        )
    
    @staticmethod
    async def delete_chat(db: AsyncSession, chat_id: UUID) -> bool:
        """Delete a chat and all its messages"""
        result = await db.execute(
            select(ChatModel).where(ChatModel.id == chat_id)
        )
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
        token_count = llm_service.count_tokens(message_data.content)
        
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
        rag_threshold: float = 0.7,
        use_deep_research: bool = False,
        max_concurrent_research_units: int = 1,
        max_researcher_iterations: int = 1,
        max_react_tool_calls: int = 1,
        max_structured_output_retries: int = 1
    ) -> AsyncGenerator[tuple[str, Optional[UUID]], None]:
        """Generate AI response for a chat message with optional RAG support"""
        logger = logging.getLogger(__name__)

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
        
        # Extract tags from user message
        tag_names = ChatService.extract_tags_from_message(user_message)
        tag_ids = await ChatService.get_tag_ids_by_names(db, tag_names) if tag_names else []
        
        # Extract document references from user message
        document_titles = ChatService.extract_document_references_from_message(user_message)
        document_ids = await ChatService.get_document_ids_by_titles(db, document_titles) if document_titles else []
        
        # Perform similarity search to retrieve relevant context if RAG is enabled
        relevant_chunks = []
        if use_rag:
            try:
                relevant_chunks = await embedding_service.similarity_search(
                    db=db,
                    query=user_message,
                    limit=rag_limit,
                    similarity_threshold=rag_threshold,
                    tag_ids=tag_ids if tag_ids else None,
                    document_ids=document_ids if document_ids else None
                )
                logger.debug("RAG relevant_chunks: %s", relevant_chunks)
                if tag_names:
                    logger.debug("Filtered by tags: %s -> %s", tag_names, tag_ids)
                if document_titles:
                    logger.debug("Filtered by documents: %s -> %s", document_titles, document_ids)
            except Exception as e:
                logger.warning("RAG similarity search failed, continuing without RAG: %s", e)
                relevant_chunks = []
        
        # Build context from retrieved chunks and prepare citation mapping
        context_parts = []
        chunk_to_citation_mapping = {}  # Maps citation numbers to chunk details
        
        if relevant_chunks:
            threshold_distance = 1.0 - rag_threshold
            using_fallback = all(getattr(chunk, 'search_distance', 0) >= threshold_distance for chunk in relevant_chunks)
            
            if using_fallback:
                context_parts.append("## Related Knowledge from Database (Less Relevant):\n")
                context_parts.append("*Note: No highly relevant matches found. The following are the closest available documents:*\n\n")
            else:
                context_parts.append("## Relevant Knowledge from Database:\n")
            
            for i, chunk in enumerate(relevant_chunks, 1):
                metadata = json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {}
                source_info = f"[Source: {getattr(chunk, 'document_title', 'Unknown')}]"
                distance = getattr(chunk, 'search_distance', 'unknown')
                
                if isinstance(distance, float):
                    confidence = f" (Similarity: {(1.0 - distance) * 100:.1f}%)"
                else:
                    confidence = ""
                
                # Store citation mapping for later use
                chunk_to_citation_mapping[i] = {
                    'chunk_id': str(chunk.id),
                    'document_id': str(chunk.document_id),
                    'document_title': getattr(chunk, 'document_title', 'Unknown'),
                    'chunk_index': chunk.chunk_index,
                    'page_number': metadata.get('page_number'),
                    'similarity': 1.0 - distance if isinstance(distance, float) else 0.0,
                    'content_preview': chunk.content[:200] + '...' if len(chunk.content) > 200 else chunk.content
                }
                
                context_parts.append(f"{i}. {source_info}{confidence}\n{chunk.content}\n")
            
            context_parts.append("\n---\n\nIMPORTANT: When citing information from these sources, use the format [N] where N is the source number (1-{len(relevant_chunks)}). Each citation should be placed immediately after the claim it supports.\n\n")
        
        # Build conversation history for LLM call
        messages = []
        for msg in sorted(chat.messages[:-1], key=lambda x: x.created_at):
            messages.append({"role": msg.role, "content": msg.content})
        
        # Base system prompt (kept as before)
        base_prompt = """You are ChatGPT, a large language model based on the GPT-5 model and trained by OpenAI.
Knowledge cutoff: 2024-06
Current date: 2025-08-08

Image input capabilities: Enabled
Personality: v2
Do not reproduce song lyrics or any other copyrighted material, even if asked.
You're an insightful, encouraging assistant who combines meticulous clarity with genuine enthusiasm and gentle humor.
Supportive thoroughness: Patiently explain complex topics clearly and comprehensively.
Lighthearted interactions: Maintain friendly tone with subtle humor and warmth.
Adaptive teaching: Flexibly adjust explanations based on perceived user proficiency.
Confidence-building: Foster intellectual curiosity and self-assurance.

IMPORTANT: When writing mathematical formulas, equations, or any LaTeX expressions:
- For display equations (centered, on their own line), use: \\begin{equation} ... \\end{equation}
- For inline math (within text), use: \\( ... \\)
- For simple inline math, you can also use: $...$
- Examples:
  * Display: \\begin{equation} E = mc^2 \\end{equation}
  * Inline: The equation \\(E = mc^2\\) shows energy-mass equivalence
  * Simple inline: The famous $E = mc^2$ equation

CITATION FORMATTING - VERY IMPORTANT:
When you reference information from the provided knowledge context, use INLINE citations immediately after the relevant claim:
- Format: "Specific claim or fact[N]" where N is the number of the source
- Place citations directly after the claim they support, not at the end of sentences or paragraphs
- Each citation [N] corresponds to the numbered source in the knowledge context
- Examples:
  * "Einstein developed the theory of relativity[1] which revolutionized physics[1]."
  * "The study found that students performed better[2] when using active learning methods[2]."
  * "Recent research shows[3] that climate change is accelerating[3]."
- Use citations liberally - every factual claim from the knowledge base should be cited
- Multiple facts from the same source should each have their own citation: "Fact A[1] and fact B[1]"

Do not end with opt-in questions or hedging closers. Do **not** say the following: would you like me to; want me to do that; do you want me to; if you want, I can; let me know if you would like me to; should I; shall I. Ask at most one necessary clarifying question at the start, not the end. If the next step is obvious, do it."""
        
        # Construct full system/context message when applicable
        if context_parts:
            if all(getattr(chunk, 'search_distance', 0) >= (1.0 - rag_threshold) for chunk in relevant_chunks):
                context_message = base_prompt + "\n\n" + "You have access to a knowledge base. The following context was retrieved but may not be highly relevant:\n\n" + "".join(context_parts)
            else:
                context_message = base_prompt + "\n\n" + "You have access to a knowledge base. Use the following context if relevant:\n\n" + "".join(context_parts)
            # prefer system role if supported by provider; we still append to messages so all providers see it
            messages.insert(0, {"role": "system", "content": context_message})
        else:
            messages.insert(0, {"role": "system", "content": base_prompt})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Prepare document references structure
        document_references = []
        if relevant_chunks:
            doc_stats = {}
            for chunk in relevant_chunks:
                doc_id = str(chunk.document_id) if hasattr(chunk, 'document_id') else None
                if doc_id and doc_id not in doc_stats:
                    doc_stats[doc_id] = {
                        'id': doc_id,
                        'title': getattr(chunk, 'document_title', 'Unknown'),
                        'source_type': getattr(chunk, 'source_type', 'unknown'),
                        'similarities': [],
                        'chunk_count': 0,
                        'chunks_used': []  # NEW: Store individual chunk details
                    }
                if doc_id:
                    doc_stats[doc_id]['chunk_count'] += 1
                    distance = getattr(chunk, 'search_distance', 0)
                    similarity = 1.0 - distance if distance is not None else 0.0
                    doc_stats[doc_id]['similarities'].append(similarity)

                    # Parse chunk metadata to get page info
                    chunk_meta = json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {}

                    # Add chunk details for highlighting
                    doc_stats[doc_id]['chunks_used'].append({
                        'chunk_id': str(chunk.id),
                        'chunk_index': chunk.chunk_index,
                        'page_number': chunk_meta.get('page_number'),
                        'page_index': chunk_meta.get('page_index'),
                        'text_position': {
                            'start': chunk_meta.get('chunk_start_char'),
                            'end': chunk_meta.get('chunk_end_char')
                        } if chunk_meta.get('chunk_start_char') is not None else None,
                        'similarity': similarity,
                        'content_preview': chunk.content[:200] + '...' if len(chunk.content) > 200 else chunk.content
                    })
            for doc_data in doc_stats.values():
                if doc_data['similarities']:
                    document_references.append({
                        'id': doc_data['id'],
                        'title': doc_data['title'],
                        'source_type': doc_data['source_type'],
                        'chunk_count': doc_data['chunk_count'],
                        'max_similarity': max(doc_data['similarities']),
                        'avg_similarity': sum(doc_data['similarities']) / len(doc_data['similarities']),
                        'chunks_used': doc_data['chunks_used'],  # NEW: Include chunk details
                        'tags': []  # TODO: Add tags in future iteration
                    })
        
        # Determine provider type (best-effort detection)
        provider_hint = ""
        try:
            provider_hint = getattr(llm_service, "provider", "") or llm_service.__class__.__name__ or str(type(llm_service))
            provider_hint = str(provider_hint).lower()
        except Exception:
            provider_hint = ""
        is_langchain = any(k in provider_hint for k in ("langchain", "ollama", "langchainollama"))
        is_openai_like = any(k in provider_hint for k in ("openai", "azure", "azure_openai", "gpt"))
        logger.debug("LLM provider hint: %s (langchain=%s, openai_like=%s)", provider_hint, is_langchain, is_openai_like)
        
        # Generate response: try several interfaces in preference order, with clear logging
        response_content = ""

        if use_deep_research:
            # Unified approach: Create assistant message immediately with "running" status
            deep_research_params = {
                "max_concurrent_research_units": max_concurrent_research_units,
                "max_researcher_iterations": max_researcher_iterations,
                "max_react_tool_calls": max_react_tool_calls,
                "max_structured_output_retries": max_structured_output_retries,
                "query": user_message
            }

            # Create assistant message using the existing add_message method
            assistant_msg = await ChatService.add_message(
                db,
                chat_id,
                MessageCreate(content="Deep research in progress...", role="assistant")
            )

            # Update with deep research specific fields
            result = await db.execute(
                select(MessageModel).where(MessageModel.id == assistant_msg.id)
            )
            db_message = result.scalar_one_or_none()
            if db_message:
                db_message.is_deep_research = True
                db_message.deep_research_status = "running"
                db_message.deep_research_params = json.dumps(deep_research_params)
                await db.commit()

            # Start deep research in background (fire and forget)
            asyncio.create_task(ChatService._run_deep_research_background(
                db, assistant_msg.id, user_message, deep_research_params
            ))

            # Return immediately - no streaming, no complex generators
            return

        # Regular chat flow - stream and save response
        try:
            # Preferred: async generator named generate_chat_completion (already used for langchain adapters)
            gen = getattr(llm_service, "generate_chat_completion", None)
            if gen and inspect.isasyncgenfunction(gen):
                logger.info("Using async generator llm_service.generate_chat_completion")
                async for chunk in gen(messages):
                    response_content += chunk
                    yield (chunk, None)
                # finished streaming
            else:
                # If provider was detected as langchain, try synchronous chat completion first, then generate
                if is_langchain:
                    logger.info("Provider appears to be LangChain-like; trying llm_service.generate_chat_completion(...) first, then generate")
                    # Try chat completion first (supports messages format)
                    chat_completion = getattr(llm_service, "generate_chat_completion", None)
                    if callable(chat_completion):
                        res = chat_completion(messages)
                        if isinstance(res, dict):
                            text = res.get("response") or res.get("text") or json.dumps(res)
                        else:
                            text = str(res)
                        response_content += text
                        yield (text, None)
                    else:
                        # Fallback to generate with prompt conversion
                        sync_gen = getattr(llm_service, "generate", None)
                        if callable(sync_gen):
                            # sync generate may return dict/text
                            prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
                            res = sync_gen(prompt)
                            if isinstance(res, dict):
                                text = res.get("response") or res.get("text") or json.dumps(res)
                            else:
                                text = str(res)
                            response_content += text
                            yield (text, None)
                        else:
                            # fallback to any callable that may accept messages
                            fallback = getattr(llm_service, "call", None) or getattr(llm_service, "run", None)
                            if callable(fallback):
                                res = fallback(messages)
                                text = res.get("response") if isinstance(res, dict) else str(res)
                                response_content += text
                                yield (text, None)
                            else:
                                raise RuntimeError("No usable LangChain interface found on llm_service")
                # Else if provider looks like OpenAI/Azure, try their typical interfaces
                elif is_openai_like:
                    logger.info("Provider appears to be OpenAI/Azure-like; trying known interfaces")
                    # 1) streaming-style method on llm_service
                    create_stream = getattr(llm_service, "stream_chat_completion", None) or getattr(llm_service, "stream", None)
                    if create_stream and inspect.iscoroutinefunction(create_stream):
                        logger.info("Using async streaming interface on llm_service")
                        async for chunk in create_stream(messages):
                            response_content += chunk
                            yield (chunk, None)
                    # 2) sync create_chat_completion or generate
                    else:
                        create = getattr(llm_service, "create_chat_completion", None) or getattr(llm_service, "generate", None) or getattr(llm_service, "chat_completion", None)
                        if callable(create):
                            # Some wrappers expect OpenAI-style 'messages' while others expect a string prompt
                            try:
                                res = create(messages)
                            except TypeError:
                                prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
                                res = create(prompt)
                            if isinstance(res, dict):
                                # try common fields
                                text = res.get("choices", [{}])[0].get("message", {}).get("content") if res.get("choices") else res.get("response") or res.get("text")
                                if not text:
                                    text = json.dumps(res)
                            else:
                                text = str(res)
                            response_content += text
                            yield (text, None)
                        else:
                            raise RuntimeError("No usable OpenAI/Azure interface found on llm_service")
                else:
                    # Unknown provider: attempt generic calls in safe order
                    logger.info("Unknown provider type; attempting generic interfaces")
                    # try async generator even if not detected
                    if gen and inspect.isasyncgenfunction(gen):
                        async for chunk in gen(messages):
                            response_content += chunk
                            yield (chunk, None)
                    elif callable(getattr(llm_service, "generate", None)):
                        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
                        res = llm_service.generate(prompt)
                        text = res.get("response") if isinstance(res, dict) else str(res)
                        response_content += text
                        yield (text, None)
                    else:
                        raise RuntimeError("llm_service does not expose a supported interface")
        except Exception as e:
            logger.exception("LLM call failed: %s", e)
            err_msg = "Fehler beim Aufruf des LLM-Service."
            response_content += err_msg
            yield (err_msg, None)
        
        # Process citations in response content to create markdown links
        print(f"📖 Processing citations with mapping: {chunk_to_citation_mapping}")
        processed_content = ChatService.process_citations_to_markdown(
            response_content,
            chunk_to_citation_mapping
        )
        print(f"📖 Original content: {response_content[:200]}...")
        print(f"📖 Processed content: {processed_content[:200]}...")
        
        # Save assistant response with processed markdown links
        assistant_msg = await ChatService.add_message(
            db,
            chat_id,
            MessageCreate(content=processed_content, role="assistant")
        )
        
        # Yield final message ID with document references and citation mapping
        yield ("", assistant_msg.id, document_references, chunk_to_citation_mapping)
    
    @staticmethod
    def process_citations_to_markdown(content: str, citation_mapping: dict) -> str:
        """Convert inline citations [1], [2] to markdown links using citation mapping"""
        print(f"📖 process_citations_to_markdown called with content length: {len(content)}")
        print(f"📖 Citation mapping: {citation_mapping}")

        if not citation_mapping:
            print("📖 No citation mapping provided, returning original content")
            return content
        
        import re
        
        def replace_citation(match):
            citation_num = int(match.group(1))
            print(f"📖 Found citation [{citation_num}]")
            citation_data = citation_mapping.get(citation_num)
            print(f"📖 Citation data for [{citation_num}]: {citation_data}")

            if not citation_data:
                # No mapping found, return original citation
                print(f"📖 No mapping found for citation [{citation_num}], keeping original")
                return match.group(0)
            
            # Extract citation data
            document_id = citation_data.get('document_id')
            chunk_id = citation_data.get('chunk_id')
            document_title = citation_data.get('document_title', 'Unknown Document')
            page_number = citation_data.get('page_number')
            
            if not document_id or not chunk_id:
                # Missing required data, return original citation
                return match.group(0)
            
            # Build URL with highlighting parameters
            url = f"/knowledge/{document_id}?chunks={chunk_id}"
            # Don't include pages parameter - let the viewer show all pages and highlight specific chunk

            # Create markdown link: [original_citation](url "title")
            title = f"{document_title}"
            if page_number:
                title += f" (Page {page_number})"

            result = f"[{match.group(0)}]({url} \"{title}\")"
            print(f"📖 Converted [{citation_num}] to markdown: {result}")
            return result
        
        # Pattern to match citations like [1], [2], etc.
        citation_pattern = r'\[(\d+)\]'
        print(f"📖 Looking for citations with pattern: {citation_pattern}")
        processed_content = re.sub(citation_pattern, replace_citation, content)

        print(f"📖 Final processed content: {processed_content[:300]}...")
        return processed_content
    
    @staticmethod
    async def get_or_create_chat(db: AsyncSession, chat_id: Optional[UUID] = None, title: str = "New Chat") -> Chat:
        """Get existing chat or create new one"""
        if chat_id:
            chat = await ChatService.get_chat(db, chat_id)
            if chat:
                return chat

        # Create new chat
        return await ChatService.create_chat(db, ChatCreate(title=title))
    
    @staticmethod
    async def _run_deep_research_background(db: AsyncSession, message_id: UUID, query: str, params: dict):
        """Run deep research in background and update message with results"""
        try:
            # Run the deep research
            research_report = await DeepResearchService.run_deep_research(
                query=query,
                max_concurrent_research_units=params.get("max_concurrent_research_units", 1),
                max_researcher_iterations=params.get("max_researcher_iterations", 1),
                max_react_tool_calls=params.get("max_react_tool_calls", 1),
                max_structured_output_retries=params.get("max_structured_output_retries", 1)
            )
            
            # Update message with results
            result = await db.execute(
                select(MessageModel).where(MessageModel.id == message_id)
            )
            message = result.scalar_one_or_none()
            
            if message:
                message.content = research_report
                message.deep_research_status = "completed"
                message.token_count = llm_service.count_tokens(research_report)
                await db.commit()
                
        except Exception as e:
            # Update message with error
            result = await db.execute(
                select(MessageModel).where(MessageModel.id == message_id)
            )
            message = result.scalar_one_or_none()
            
            if message:
                error_message = f"Deep research failed: {str(e)}"
                message.content = error_message
                message.deep_research_status = "failed"
                message.deep_research_error = str(e)
                await db.commit()
    
    @staticmethod
    async def get_message_status(db: AsyncSession, message_id: UUID) -> Optional[dict]:
        """Get deep research status for a message"""
        # Get the message
        result = await db.execute(
            select(MessageModel)
            .where(MessageModel.id == message_id)
        )
        message = result.scalar_one_or_none()
        
        if not message:
            return None
            
        return {
            "id": str(message.id),
            "content": message.content,
            "is_deep_research": message.is_deep_research,
            "status": message.deep_research_status,
            "error": message.deep_research_error,
            "created_at": message.created_at.isoformat() if message.created_at else None
        }
