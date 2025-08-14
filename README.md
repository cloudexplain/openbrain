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
│   │   │   └── chat.py         # Chat API endpoints
│   │   ├── models/
│   │   │   ├── database.py     # SQLAlchemy async setup
│   │   │   └── chat.py         # Database models (Chat, Message, Document)
│   │   ├── schemas/
│   │   │   └── chat.py         # Pydantic models for API
│   │   ├── services/
│   │   │   ├── azure_openai.py # Azure OpenAI integration
│   │   │   └── chat_service.py # Business logic
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

### 🔜 Still To Do

1. **Add document upload endpoint**
   - File upload handling
   - Text extraction from PDFs/DOCX
   - Chunking strategy for documents

2. **Enhance chat responses with RAG**
   - Retrieve relevant context before generating response
   - Augment prompts with retrieved information
   - Citation and source tracking in responses

3. **Document management UI**
   - View all documents in knowledge base
   - Delete or update documents
   - Preview document chunks and embeddings

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