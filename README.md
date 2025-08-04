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

**🚧 Phase 2 - Database & RAG (READY TO IMPLEMENT)**
- PostgreSQL database with pgvector extension setup
- Document ingestion pipeline (PDF, TXT, DOCX support)
- Text chunking and embedding generation
- Vector similarity search for context retrieval
- RAG-powered responses with retrieved context
- Document management and document_metadata storage

**🔮 Phase 3 - Advanced Features (PLANNED)**
- User authentication and authorization
- Multi-user collaboration features
- Document sharing and permissions
- Advanced search and filtering
- Conversation export and analytics
- API rate limiting and monitoring

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

- **Node.js 18+** with npm
- **Python 3.11+** with pip
- **Azure OpenAI API access** with:
  - GPT-4 deployment (for chat completions)
  - text-embedding-ada-002 deployment (for future RAG features)
- **PostgreSQL 14+** (for database features - coming in Phase 2)

### 1. Backend Setup

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
nano .env  # or use your preferred editor
```

**Required .env variables:**
```env
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-ada-002
```

```bash
# Start the development server
python run.py
```

✅ **Backend available at:** `http://localhost:8000`  
📚 **API Documentation:** `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

✅ **Frontend available at:** `http://localhost:5173`

### 3. Test the System

1. Open `http://localhost:5173` in your browser
2. Start a conversation - try "Hello, how can you help me?"
3. Watch real-time streaming responses
4. Create multiple chats to test session management
5. Test chat deletion and navigation

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
    filename VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size INTEGER NOT NULL,
    document_metadata TEXT,  -- JSON
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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

### 🚧 Phase 2: Database & RAG Integration (NEXT)
- [ ] PostgreSQL + pgvector database setup
- [ ] Alembic database migrations
- [ ] Document upload API (PDF, TXT, DOCX)
- [ ] Text chunking and embedding pipeline
- [ ] Vector similarity search
- [ ] RAG-enhanced chat responses
- [ ] Document management interface

### 🔮 Phase 3: Advanced Features (PLANNED)
- [ ] User authentication and authorization
- [ ] Multi-user collaboration features
- [ ] Document sharing and permissions
- [ ] Advanced search and filtering
- [ ] Conversation export (JSON, Markdown)
- [ ] Usage analytics and monitoring
- [ ] API rate limiting
- [ ] Docker containerization
- [ ] Production deployment guides

## 🚀 Next Steps to Add RAG

Ready to add RAG functionality? Here's your roadmap:

1. **Set up PostgreSQL + pgvector**
   ```bash
   # Add to database/ directory
   docker-compose up -d postgres
   ```

2. **Run database migrations**
   ```bash
   cd backend
   alembic upgrade head
   ```

3. **Add document upload endpoint**
   - File upload handling
   - Text extraction from PDFs/DOCX
   - Chunking strategy implementation

4. **Implement vector search**
   - Generate embeddings for document chunks
   - Similarity search queries
   - Context retrieval for chat

5. **Enhance chat responses**
   - Retrieve relevant context
   - Augment prompts with retrieved information
   - Citation and source tracking

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