# SecondBrain - Collaborative AI Assistant with RAG

A modern, production-ready chat interface for AI assistance with document ingestion and RAG (Retrieval Augmented Generation) capabilities. Built with SvelteKit frontend and FastAPI backend using Microsoft Azure OpenAI.

## 🚀 Current Status

**✅ Phase 1 - Core Chat System (COMPLETE)**
- Modern Claude-style chat interface with TailwindCSS v3
- Real-time message streaming via Server-Sent Events (SSE)
- Complete chat session management (create, load, delete, persist)
- Responsive sidebar with chat history and search
- Python FastAPI backend with async Azure OpenAI integration
- Full TypeScript integration with type safety
- SQLAlchemy ORM models ready for PostgreSQL + pgvector
- Production-ready error handling and logging
- CORS configured for local and production deployment

**✅ Phase 2 - Database & RAG (COMPLETE)**
- ✅ PostgreSQL database with pgvector extension setup
- ✅ Chat conversations can be saved as documents (source_type: "chat")
- ✅ Text chunking and embedding generation for chats
- ✅ Vector similarity search with source filtering
- ✅ Document ingestion pipeline (PDF, TXT, DOCX, MD support)
- ✅ Async document upload with push notifications
- ✅ RAG-powered responses with retrieved context
- ✅ Knowledge base management interface

**✅ Phase 2.5 - Document Tagging System (COMPLETE)**
- ✅ Tag management system with CRUD operations
- ✅ Many-to-many document-tag relationships
- ✅ Visual tag interface with color coding
- ✅ Tag assignment to documents in knowledge base
- ✅ Tag-filtered RAG search in chat (`#tagname` syntax)
- ✅ Smart tag autocomplete in chat interface
- ✅ Tag-based document filtering and organization

**🚧 Phase 3 - Production & Advanced Features (IN PROGRESS)**
- ✅ Docker containerization (development & production modes)
- ✅ Production deployment guides with Azure Files support
- Multi-user authentication and collaboration features
- Advanced search, filtering, and document management
- Conversation export, analytics, and API rate limiting

## 📁 Project Structure

```
secondbrain/
├── frontend/                    # SvelteKit Frontend
│   ├── src/
│   │   ├── lib/
│   │   │   ├── components/     # Svelte components (ChatMessage, Sidebar, etc.)
│   │   │   └── api.ts          # API client with TypeScript types
│   │   ├── routes/
│   │   │   ├── +layout.svelte  # Root layout with CSS imports
│   │   │   └── +page.svelte    # Main chat interface
│   │   └── app.pcss           # TailwindCSS imports
│   ├── package.json
│   ├── tailwind.config.js     # TailwindCSS v3 configuration
│   └── vite.config.ts
│
├── backend/                     # FastAPI Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── chat.py         # Chat API endpoints
│   │   │   ├── tags.py         # Tag management API endpoints
│   │   │   └── document_tags.py # Document-tag association endpoints
│   │   ├── models/
│   │   │   ├── database.py     # SQLAlchemy async setup
│   │   │   └── chat.py         # Database models (Chat, Message, Document, Tag)
│   │   ├── schemas/
│   │   │   ├── chat.py         # Pydantic models for API
│   │   │   └── tag.py          # Tag-related Pydantic models
│   │   ├── services/
│   │   │   ├── azure_openai.py # Azure OpenAI integration
│   │   │   ├── chat_service.py # Business logic with tag filtering
│   │   │   └── embedding_service.py # Vector search with tag filtering
│   │   ├── config.py           # Settings and environment variables
│   │   └── main.py             # FastAPI application
│   ├── alembic/                # Database migrations
│   ├── requirements.txt        # Python dependencies
│   ├── run.py                  # Development server
│   └── .env.example            # Environment template
│
├── database/                    # Database Setup (Future)
│   └── docker-compose.yml      # PostgreSQL + pgvector container
│
└── README.md                   # This documentation
```

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended)
- **Azure OpenAI API access** with:
  - GPT-4 deployment (for chat completions)
  - text-embedding-ada-002 deployment (for embeddings)

### Option 1: Docker Compose (Recommended)

#### Development Mode

```bash
# Clone the repository
git clone <repository-url>
cd secondbrain

# Start in development mode with hot-reloading
./dev.sh

# Or manually:
docker-compose -f docker-compose.dev.yml up
```

✅ **Application available at:** `http://localhost:5173`  
📚 **API Documentation:** `http://localhost:8000/docs`

#### Production Mode

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Start in production mode
./prod.sh --build

# Or manually:
docker-compose -f docker-compose.prod.yml up --build
```

✅ **Application available at:** `http://localhost:3000`  
📚 **API Documentation:** `http://localhost:8000/docs`

### Option 2: Manual Setup

If you prefer to run without Docker:

#### 1. Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Start the development server
python run.py
```

#### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### 3. Database Setup

```bash
# Start PostgreSQL with pgvector
docker run -d \
  --name secondbrain-postgres \
  -e POSTGRES_DB=secondbrain \
  -e POSTGRES_USER=secondbrain \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 3. Test the System

1. Open the application in your browser
2. Start a conversation - try "Hello, how can you help me?"
3. Upload documents (PDF, TXT, MD, DOCX) to the knowledge base
4. Test RAG-powered responses with your uploaded content
5. Save conversations to knowledge base for future reference

### 4. Try the Tag System

1. **Create Tags**: Click the orange "Tags" button in sidebar → Create tags like "Python", "Machine Learning", "DevOps"
2. **Tag Documents**: Open knowledge base → Select a document → Add tags using the tag selector
3. **Smart Chat Search**: Ask questions with hashtags:
   - `"What are Python best practices for #web-development?"`
   - `"Show me #docker deployment strategies"`
   - `"Help with #machine-learning model training"`

The system will automatically search only documents tagged with those specific tags!

## 🐳 Docker Deployment

### Development vs Production

This project includes separate configurations for different deployment scenarios:

| Feature | Development | Production |
|---------|------------|------------|
| **Docker Compose File** | `docker-compose.dev.yml` | `docker-compose.prod.yml` |
| **Source Code** | Mounted as volumes | Copied into image |
| **Hot Reload** | Yes | No |
| **Build Optimization** | No | Yes |
| **Security** | Runs as root | Runs as non-root user |
| **Frontend Build** | Dev server | Production build |
| **Backend Server** | Development mode | Production mode |
| **Uploads Directory** | Local mount | Docker volume |

### Development Mode

Perfect for development with hot-reloading and easy debugging:

```bash
# Quick start
./dev.sh

# With specific options
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml logs -f
```

**Features:**
- Source code mounted as volumes
- Automatic restart on file changes
- Debug mode enabled
- Direct file editing capability

### Production Mode

Optimized for deployment with security and performance:

```bash
# Configure environment
cp .env.example .env
# Edit .env with your production settings

# Deploy
./prod.sh --build
```

**Features:**
- Optimized Docker images
- No source code mounts (everything copied)
- Production builds of frontend
- Non-root users for security
- Environment variable configuration

### Environment Configuration

Production mode requires a `.env` file with your settings:

```env
# PostgreSQL Configuration
POSTGRES_USER=secondbrain
POSTGRES_PASSWORD=your_secure_password_here

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=your-embedding-deployment-name
AZURE_OPENAI_API_VERSION=2023-05-15

# Port Configuration (optional)
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

### Azure Storage Integration

For production deployments, you can easily switch to Azure Files for document storage:

```yaml
# In docker-compose.prod.yml
volumes:
  uploads:
    driver: azure_file
    driver_opts:
      share_name: secondbrain-uploads
      storage_account_name: ${AZURE_STORAGE_ACCOUNT}
```

This seamless volume abstraction means no code changes are needed to switch between local storage and Azure Files.

### Helper Scripts

- `./dev.sh` - Quick development startup
- `./prod.sh` - Production startup with environment validation

For more detailed deployment information, see [`DEPLOYMENT.md`](./DEPLOYMENT.md).

## ⚙️ Configuration

### Backend Environment Variables

Complete `.env` configuration:

```env
# Azure OpenAI Configuration (Required)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2023-12-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-ada-002

# Database Configuration (Phase 2)
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/secondbrain
POSTGRES_USER=secondbrain
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=secondbrain

# CORS Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:4173
```

### Frontend Configuration

The frontend automatically connects to `http://localhost:8000/api/v1` by default. To change this, edit `frontend/src/lib/api.ts`:

```typescript
const API_BASE_URL = 'http://localhost:8000/api/v1';  // Change this for production
```

## 🔌 API Endpoints

### Chat Management

| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `GET` | `/api/v1/chats` | Get all chats with document_metadata | ✅ |
| `POST` | `/api/v1/chats` | Create new chat | ✅ |
| `GET` | `/api/v1/chats/{id}` | Get chat with full message history | ✅ |
| `DELETE` | `/api/v1/chats/{id}` | Delete chat and all messages | ✅ |
| `GET` | `/api/v1/chats/{id}/messages` | Get messages for specific chat | ✅ |

### Chat Interaction

| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `POST` | `/api/v1/chat` | Send message, get streaming response | ✅ |
| `POST` | `/api/v1/chats/{id}/save-to-knowledge` | Save chat as document with embeddings | ✅ |

### Knowledge Base

| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `POST` | `/api/v1/search` | Vector similarity search across documents | ✅ |

### Tag Management

| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `GET` | `/api/v1/tags` | List all tags with document counts | ✅ |
| `POST` | `/api/v1/tags` | Create new tag | ✅ |
| `GET` | `/api/v1/tags/{tag_id}` | Get specific tag | ✅ |
| `PUT` | `/api/v1/tags/{tag_id}` | Update tag | ✅ |
| `DELETE` | `/api/v1/tags/{tag_id}` | Delete tag | ✅ |
| `GET` | `/api/v1/tags/{tag_id}/documents` | Get all documents with specific tag | ✅ |

### Document-Tag Associations

| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `GET` | `/api/v1/documents/{doc_id}/tags` | Get tags for document | ✅ |
| `POST` | `/api/v1/documents/{doc_id}/tags` | Add tags to document | ✅ |
| `PUT` | `/api/v1/documents/{doc_id}/tags` | Replace all tags for document | ✅ |
| `DELETE` | `/api/v1/documents/{doc_id}/tags/{tag_id}` | Remove tag from document | ✅ |

### System

| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `GET` | `/` | API status | ✅ |
| `GET` | `/health` | Health check | ✅ |
| `GET` | `/docs` | Interactive API documentation | ✅ |

### API Usage Examples

#### Send Chat Message (Streaming)

```javascript
const response = await fetch('http://localhost:8000/api/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "Explain quantum computing in simple terms",
    chat_id: null // Creates new chat, or use existing chat ID
  })
});

// Handle Server-Sent Events streaming response
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      
      if (data.type === 'content') {
        console.log('Streaming content:', data.content);
      } else if (data.type === 'done') {
        console.log('Message complete:', data.message_id);
      }
    }
  }
}
```

#### Get Chat History

```javascript
// Get all chats
const chats = await fetch('http://localhost:8000/api/v1/chats').then(r => r.json());

// Get specific chat with messages
const chat = await fetch(`http://localhost:8000/api/v1/chats/${chatId}`).then(r => r.json());
```

## 🏗️ Architecture Overview

### Frontend Stack (SvelteKit + TypeScript)
- **Framework**: SvelteKit with Vite for fast development
- **Styling**: TailwindCSS v3 with custom components
- **Type Safety**: Full TypeScript integration
- **Real-time**: Server-Sent Events for streaming responses
- **State Management**: Reactive Svelte stores
- **Components**: Modular, reusable UI components

### Backend Stack (FastAPI + Python)
- **Framework**: FastAPI with async/await support
- **AI Integration**: Azure OpenAI with streaming completions
- **Database**: SQLAlchemy ORM with async PostgreSQL
- **Validation**: Pydantic models for request/response validation
- **Documentation**: Auto-generated OpenAPI/Swagger docs
- **Migration**: Alembic for database schema management

### Database Design (PostgreSQL + pgvector)

**Current Models (Ready for Implementation):**

```sql
-- Core chat functionality
CREATE TABLE chats (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY,
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    role VARCHAR(20) CHECK (role IN ('user', 'assistant')),
    token_count INTEGER,
    embedding VECTOR(1536),  -- OpenAI ada-002 dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RAG document support (Phase 2)
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,  -- 'chat', 'file', 'url', etc.
    source_id VARCHAR(255),  -- chat_id, file_path, url, etc.
    filename VARCHAR(255),  -- Only for file source_type
    file_type VARCHAR(50),  -- Only for file source_type
    file_size INTEGER,  -- Only for file source_type
    document_metadata TEXT,  -- JSON for source-specific metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    document_metadata TEXT,  -- JSON
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tagging system (Phase 2.5)
CREATE TABLE tags (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#808080',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE document_tags (
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (document_id, tag_id)
);

-- Indexes for performance
CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_document_tags_document ON document_tags(document_id);
CREATE INDEX idx_document_tags_tag ON document_tags(tag_id);
```

### Data Flow Architecture

```
┌─────────────────┐    HTTP/SSE     ┌──────────────────┐    OpenAI API    ┌─────────────────┐
│   SvelteKit     │◄────────────────┤    FastAPI       │◄─────────────────┤  Azure OpenAI   │
│   Frontend      │                 │    Backend       │                  │   (GPT-4)       │
└─────────────────┘                 └──────────────────┘                  └─────────────────┘
         │                                     │
         │                                     │ SQLAlchemy
         │                                     ▼
         │                          ┌──────────────────┐
         │                          │   PostgreSQL     │
         │                          │   + pgvector     │
         └──────────────────────────┤   Database       │
              WebSocket (Future)    └──────────────────┘
```

## 🗺️ Development Roadmap

### ✅ Phase 1: Core Chat System (COMPLETE)
- [x] SvelteKit frontend with TailwindCSS
- [x] FastAPI backend with Azure OpenAI
- [x] Real-time streaming chat
- [x] Session management
- [x] TypeScript integration
- [x] Production-ready error handling

### ✅ Phase 2: Database & RAG Integration (COMPLETE)
- [x] PostgreSQL + pgvector database setup
- [x] Alembic database migrations
- [x] Chat conversations as searchable documents
- [x] Text chunking and embedding pipeline for chats
- [x] Vector similarity search with source filtering
- [x] Save chat to knowledge base functionality
- [x] Document upload API (PDF, TXT, DOCX, MD)
- [x] Async document processing with push notifications
- [x] RAG-enhanced chat responses
- [x] Knowledge base management interface

### ✅ Phase 2.5: Document Tagging System (COMPLETE)
- [x] Tag database schema with many-to-many relationships
- [x] Tag CRUD API endpoints with full validation
- [x] Document-tag association management
- [x] Visual tag management interface
- [x] Color-coded tags with descriptions
- [x] Tag assignment to documents in knowledge base
- [x] Tag-filtered RAG search (`#tagname` syntax in chat)
- [x] Smart tag parsing and autocomplete
- [x] Tag-based document organization and filtering

### 🚧 Phase 3: Production & Advanced Features (IN PROGRESS)
- [x] Docker containerization (dev & prod)
- [x] Production deployment guides
- [x] Azure Files integration for uploads
- [ ] User authentication and authorization
- [ ] Multi-user collaboration features
- [ ] Document sharing and permissions
- [ ] Advanced search and filtering
- [ ] Conversation export (JSON, Markdown)
- [ ] Usage analytics and monitoring
- [ ] API rate limiting
- [ ] SSL/TLS configuration

## 💭 Future Enhancement: Advanced RAG for Large Documents

### Current RAG Limitations

The current RAG implementation works well for targeted queries but has limitations with large documents:

- **Limited Context Window**: RAG retrieves only top-k chunks (typically 3-5)
- **Fragmented Understanding**: Large documents get broken into chunks, losing overall structure
- **Poor Summarization**: Document-wide analysis requires broader context than current chunk retrieval provides
- **Missing Document Structure**: System can't "see" document hierarchy, sections, or overall themes

### Proposed Solution: Automated Document Summaries + Smart Context Expansion

**🎯 Primary Approach: Pre-computed Hierarchical Summaries**

The most promising solution is to generate and store multiple levels of summaries when documents are uploaded:

```
Document Upload Pipeline:
1. Original Document → Chunked for detailed RAG
2. Generate Executive Summary (2-3 sentences)
3. Generate Section Summaries (paragraph per major section)
4. Generate Detailed Summary (comprehensive overview)
5. Store document outline/structure metadata
```

**Benefits:**
- ✅ Fast retrieval for summary queries
- ✅ Consistent summary quality
- ✅ No real-time complexity or latency
- ✅ Multiple granularity levels available
- ✅ Document structure preserved

**Usage Examples:**
```javascript
// Query types would automatically select appropriate summary level:
"What is this document about?" → Executive Summary
"Summarize the methodology section" → Section Summary 
"Give me a comprehensive overview" → Detailed Summary + key chunks
"What does it say about performance?" → Standard RAG chunks
```

### Alternative Approaches Considered

**Option 2: Smart Context Expansion (Hybrid)**
- Detect when queries need document-wide understanding
- Expand chunk retrieval (5-15 chunks) + add document metadata
- Two-tier system: standard vs expanded RAG

**Pros:** Adaptive, maintains performance for simple queries
**Cons:** Decision boundary is fuzzy, potential context window limits

**Option 3: Multi-Step RAG with Planning**
- AI analyzes query and creates retrieval plan
- Multiple targeted RAG queries based on plan
- Synthesize results from multiple searches

**Pros:** Most flexible, works for complex analysis tasks  
**Cons:** High latency, multiple API calls, complexity

**Option 4: Progressive/Adaptive RAG**
- Start with standard RAG
- If AI confidence is low, automatically expand context
- Show progression: "Let me get more context..." → better answer

**Pros:** User sees the process, adaptive based on results
**Cons:** Still faces decision boundary challenges

### Implementation Roadmap

**Phase 1: Automated Summaries (Recommended)**
1. Extend document upload pipeline to generate summaries
2. Add summary storage to database schema
3. Modify RAG query routing to use summaries for appropriate queries
4. Add summary management in knowledge base UI

**Phase 2: Smart Context Expansion** 
1. Implement query intent classification
2. Add expanded RAG mode with more chunks + metadata
3. Fine-tune decision logic based on usage patterns

**Phase 3: Advanced Features**
1. Multi-step RAG for complex analysis tasks
2. Document outline integration for structured queries
3. Cross-document synthesis for research queries

### Technical Considerations

**Storage Requirements:**
- Executive summaries: ~100-200 tokens per document
- Section summaries: ~500-1000 tokens per document  
- Detailed summaries: ~1000-2000 tokens per document
- Estimated 10-20% increase in storage per document

**Query Routing Logic:**
```python
def select_rag_strategy(query, referenced_docs):
    summary_triggers = ["summarize", "overview", "explain the whole", "main points"]
    
    if any(trigger in query.lower() for trigger in summary_triggers):
        return "summary_mode"
    elif referenced_docs and len(query.split()) < 8:
        return "detailed_summary_mode" 
    else:
        return "standard_rag_mode"
```

**API Extensions:**
- `/api/v1/documents/{id}/summary?level=executive|detailed|sections`
- Enhanced chat endpoint with summary integration
- Summary regeneration capabilities for updated documents

### Next Steps

1. **Research Phase**: Analyze current document corpus to understand summary needs
2. **Prototype**: Implement basic executive summary generation
3. **A/B Testing**: Compare summary-enhanced vs standard RAG responses
4. **Iterative Improvement**: Refine summary generation prompts and routing logic
5. **Scale**: Roll out to full document corpus with background processing

This approach provides the best balance of performance, consistency, and user experience while addressing the core limitations of chunk-based RAG for document-wide understanding.

## 🧠 Future Enhancement: Short-Term Memory System

### Current Conversation Limitations

The current chat system treats each conversation as isolated, leading to several limitations:

- **No Cross-Conversation Context**: Each chat session starts fresh without knowledge of previous interactions
- **Limited Working Memory**: AI only has access to current conversation history within token limits
- **Repeated Explanations**: Users must re-establish context and preferences in each new chat
- **Lost Insights**: Valuable insights and patterns from recent conversations are not retained
- **No Learning**: System doesn't adapt to user's communication style or recurring needs

### Proposed Solution: Sliding Window Short-Term Memory

**🎯 Core Concept: Contextual Memory Bridge**

Implement a sliding window memory system that maintains context across recent conversations while respecting privacy and performance constraints:

```
Recent Memory Window (7-14 days):
1. Key Topics & Entities → Extracted and weighted by recency/frequency
2. User Preferences → Communication style, preferred explanations depth
3. Ongoing Projects → Multi-session work contexts
4. Recent Insights → Important conclusions and decisions
5. Conversation Patterns → Common question types and domains
```

### Technical Architecture

**Memory Storage Design:**
```sql
-- Short-term memory storage
CREATE TABLE memory_contexts (
    id UUID PRIMARY KEY,
    user_id UUID, -- Future: for multi-user support
    context_type VARCHAR(50), -- 'topic', 'preference', 'project', 'insight'
    content TEXT NOT NULL,
    entities JSONB, -- Extracted entities (people, places, concepts)
    relevance_score FLOAT DEFAULT 1.0,
    decay_factor FLOAT DEFAULT 0.95, -- Daily relevance decay
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE -- Automatic cleanup
);

-- Conversation-to-memory links
CREATE TABLE conversation_memory_links (
    conversation_id UUID REFERENCES chats(id) ON DELETE CASCADE,
    memory_context_id UUID REFERENCES memory_contexts(id) ON DELETE CASCADE,
    relevance_score FLOAT DEFAULT 1.0,
    PRIMARY KEY (conversation_id, memory_context_id)
);

-- Memory decay and access tracking
CREATE INDEX idx_memory_contexts_decay ON memory_contexts(decay_factor, last_accessed);
CREATE INDEX idx_memory_contexts_expiry ON memory_contexts(expires_at);
```

**Memory Processing Pipeline:**
```python
class ShortTermMemoryService:
    
    async def extract_conversation_context(self, chat: Chat) -> List[MemoryContext]:
        """Extract key information from completed conversation"""
        # 1. Entity extraction (people, projects, concepts)
        # 2. Topic identification and weighting
        # 3. User preference detection (explanation style, depth)
        # 4. Decision points and conclusions
        # 5. Ongoing project identification
        
    async def update_memory_relevance(self):
        """Daily task: apply decay factors and cleanup expired memories"""
        # Apply time-based decay (0.95 daily factor)
        # Remove memories below threshold (0.1 relevance)
        # Consolidate similar/duplicate memories
        
    async def retrieve_relevant_memories(self, query: str, limit: int = 5) -> List[MemoryContext]:
        """Get relevant short-term memories for current query"""
        # Vector similarity search on memory content
        # Weight by recency and relevance score
        # Filter by user context
```

### Memory Integration with Chat

**Enhanced Chat Context Flow:**
```python
async def generate_response_with_memory(
    db: AsyncSession,
    chat_id: UUID,
    user_message: str,
    use_rag: bool = True,
    use_memory: bool = True
) -> AsyncGenerator:
    
    # 1. Standard RAG retrieval (current implementation)
    rag_context = await embedding_service.similarity_search(...)
    
    # 2. Short-term memory retrieval (NEW)
    if use_memory:
        memory_contexts = await memory_service.retrieve_relevant_memories(
            query=user_message,
            user_id=current_user_id, 
            limit=3
        )
    
    # 3. Enhanced system prompt construction
    system_prompt = build_enhanced_system_prompt(
        base_prompt=base_system_prompt,
        rag_context=rag_context,
        memory_context=memory_contexts,  # NEW
        conversation_history=chat.messages
    )
```

**Memory-Enhanced System Prompt Example:**
```
You are ChatGPT with access to:

## Recent Context (Short-term Memory):
- Project Context: User is working on a SvelteKit application with FastAPI backend (discussed 3 days ago)
- Communication Style: Prefers detailed technical explanations with code examples
- Ongoing Topics: Docker deployment, RAG implementation, TypeScript integration
- Recent Decisions: Chose PostgreSQL over MongoDB for vector storage (2 days ago)

## Current Knowledge Base (RAG):
[Standard RAG context...]

## Conversation History:
[Current chat messages...]

Based on this context, respond naturally while maintaining awareness of the user's ongoing projects and preferences.
```

### Memory Types and Examples

**1. Topic Continuity**
```
Previous Chat: "Help me implement authentication in my SvelteKit app"
Current Chat: "How do I add rate limiting?"
Memory Bridge: Knows you're still working on the same SvelteKit project
```

**2. Preference Learning**
```
Memory: User prefers TypeScript examples over JavaScript
Memory: User wants production-ready code with error handling
Auto-adapts: Provides TypeScript examples with comprehensive error handling
```

**3. Project Context**
```
Memory: Working on SecondBrain chat application
Memory: Using Azure OpenAI, PostgreSQL, Docker
Current Query: "How to optimize performance?"
Context: Knows to suggest database indexing, caching, Azure-specific optimizations
```

**4. Decision Tracking**
```
Memory: Decided against using WebSocket in favor of SSE (1 week ago)
Current Query: "Should I implement real-time features?"
Response: References previous decision and builds on established architecture
```

### Implementation Phases

**Phase 1: Basic Memory Extraction (2-3 days)**
- Implement conversation analysis to extract key topics
- Store basic memory contexts with decay system
- Add memory cleanup background tasks

**Phase 2: Memory Integration (2-3 days)**
- Integrate memory retrieval into chat generation
- Implement memory-enhanced system prompts
- Add memory relevance scoring and ranking

**Phase 3: Advanced Features (1-2 weeks)**
- User preference learning and adaptation
- Project context tracking across conversations
- Memory consolidation and deduplication
- Memory management UI (view/edit/delete memories)

**Phase 4: Intelligence Layer (Future)**
- Proactive memory suggestions ("Based on your recent work...")
- Memory-driven conversation starters
- Cross-user memory insights (with permission)
- Long-term memory promotion (important contexts → permanent knowledge)

### Privacy and Performance Considerations

**Privacy Controls:**
- Automatic expiration (7-14 day sliding window)
- User control over memory retention
- Memory deletion on user request
- No sensitive data extraction (passwords, keys, personal info)

**Performance Optimizations:**
- Background processing for memory extraction
- Efficient vector similarity search
- Memory consolidation to prevent storage bloat
- Configurable memory depth and retention

**Storage Impact:**
- Estimated 5-10KB per conversation in memory contexts
- 70-140KB per user per week (assuming 2 chats/day)
- Automatic cleanup keeps storage bounded
- Much smaller footprint than full conversation storage

### User Experience Enhancements

**Invisible Intelligence:**
- Conversations feel more natural and connected
- AI "remembers" your projects and preferences
- Reduced need to re-establish context
- Smoother multi-session workflows

**Optional Transparency:**
```
[Memory: Working on Docker deployment for SecondBrain app]
Based on your recent work with Docker, here's how to optimize your container build times...
```

**Memory Management UI:**
- View active memory contexts
- Edit or delete specific memories
- Adjust memory retention settings
- Memory insights and patterns

### Benefits Over Alternatives

**vs. Longer Context Windows:**
- ✅ Focuses on relevant information, not all history
- ✅ Maintains performance with large conversation histories  
- ✅ Respects token limits while preserving key context

**vs. Full Conversation Search:**
- ✅ Pre-processed and weighted information
- ✅ Faster retrieval than searching all conversations
- ✅ Intelligent summarization vs. raw text

**vs. Manual Context Management:**
- ✅ Automatic and invisible to user
- ✅ Learns user patterns and preferences
- ✅ No user effort required to maintain context

This short-term memory system would transform SecondBrain from a collection of isolated conversations into a truly intelligent assistant that learns and adapts to each user's working patterns and needs.

---

## 🚀 Next Steps to Add RAG

### ✅ Already Implemented
- **Chat-to-Document Conversion**: Chat conversations can be saved as searchable documents
- **Vector Embeddings**: Automatic embedding generation for chat messages
- **Similarity Search**: Vector search with source type filtering
- **Knowledge Base API**: Endpoints for saving and searching knowledge

### 📝 How to Use Current Features

1. **Save a chat to knowledge base:**
   ```javascript
   // After a chat conversation
   const result = await apiClient.saveChatToKnowledge(chatId);
   // Returns: { message, chunks_created, document_id }
   ```

2. **Search across all knowledge:**
   ```javascript
   const results = await apiClient.searchKnowledge(
     "your search query",
     5,  // limit
     0.7,  // similarity threshold
     ["chat", "file"]  // optional source type filter
   );
   ```

3. **Use the Tagging System:**
   
   **Create and Manage Tags:**
   - Click the orange "Tags" button in the sidebar
   - Create tags with custom colors and descriptions
   - Edit or delete existing tags
   
   **Tag Documents:**
   - Open a document in the knowledge base
   - Use the tag selector to add/remove tags
   - Tags are visually displayed with colors
   
   **Tag-Filtered Chat Search:**
   ```
   Chat: "What are the best practices for #python development?"
   Chat: "Show me all #machine-learning algorithms from my notes"
   Chat: "Help me with #docker deployment using my saved guides"
   ```
   
   **Tag API Usage:**
   ```javascript
   // Get all tags
   const tags = await fetch('/api/v1/tags').then(r => r.json());
   
   // Add tags to a document
   await fetch(`/api/v1/documents/${docId}/tags`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ tag_ids: [tagId1, tagId2] })
   });
   
   // Search with tag filtering automatically happens when using #hashtags in chat
   ```

### 🔜 Still To Do

1. **Advanced Tag Features**
   - Tag hierarchies (parent-child relationships)
   - Tag synonyms and aliases
   - Bulk tag operations
   - Tag usage analytics and statistics
   - Tag import/export functionality

2. **Enhanced Search & Filtering**
   - Complex tag queries with AND/OR/NOT logic
   - Tag-based document recommendations  
   - Smart tag suggestions based on document content
   - Tag combination filters in knowledge base UI
   - Search within specific tag combinations

3. **User Experience Improvements**
   - Tag templates for common document types
   - Keyboard shortcuts for tag operations
   - Tag cloud visualization
   - Drag-and-drop tag assignment
   - Tag merge and split functionality

## 🤝 Contributing

This codebase is designed for collaboration and extension:

### Project Structure Guide
- **Frontend**: `frontend/src/` - Svelte components and TypeScript
- **Backend**: `backend/app/` - FastAPI application code
- **Models**: `backend/app/models/` - Database models and schemas
- **API Routes**: `backend/app/api/` - REST endpoints
- **Services**: `backend/app/services/` - Business logic and integrations

### Development Guidelines
1. Follow existing code patterns and style
2. Add TypeScript types for all new features
3. Include error handling and logging
4. Update API documentation
5. Test streaming functionality thoroughly
6. Consider async/await patterns for database operations

### Key Integration Points
- **Azure OpenAI**: `backend/app/services/azure_openai.py`
- **Database**: `backend/app/models/` and `backend/app/services/`
- **API Client**: `frontend/src/lib/api.ts`
- **UI Components**: `frontend/src/lib/components/`

## 📄 License

**MIT License** - Feel free to use this as a foundation for your own AI assistant projects!

---

## 🆘 Troubleshooting

### Common Issues

**Backend fails to start:**
- Check Azure OpenAI credentials in `.env`
- Verify Python dependencies are installed
- Ensure port 8000 is not in use

**Frontend shows connection errors:**
- Confirm backend is running on port 8000
- Check CORS settings in `backend/app/config.py`
- Verify API_BASE_URL in `frontend/src/lib/api.ts`

**Streaming responses not working:**
- Check browser console for JavaScript errors
- Verify Server-Sent Events support
- Test API endpoints directly at `/docs`

**Need help?** Check the auto-generated API documentation at `http://localhost:8000/docs` when the backend is running.