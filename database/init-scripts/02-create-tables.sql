-- SecondBrain Database Schema
-- This script creates all necessary tables for the SecondBrain application

-- Set the search path to ensure we're working in the right schema
SET search_path TO public;

-- Create chats table
CREATE TABLE IF NOT EXISTS chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    token_count INTEGER,
    embedding VECTOR(1536), -- OpenAI text-embedding-ada-002 dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create documents table for RAG functionality
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size INTEGER NOT NULL,
    document_metadata TEXT, -- JSON string for additional metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create document_chunks table for RAG functionality
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    embedding VECTOR(1536) NOT NULL, -- Required for semantic search
    document_metadata TEXT, -- JSON string for chunk-specific metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

CREATE INDEX IF NOT EXISTS idx_chats_created_at ON chats(created_at);
CREATE INDEX IF NOT EXISTS idx_chats_updated_at ON chats(updated_at);

CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_chunk_index ON document_chunks(chunk_index);

-- Create vector indexes for similarity search (pgvector)
-- Note: These will be created when we have data, as they require non-empty tables
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_embedding ON messages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at on chats table
DROP TRIGGER IF EXISTS update_chats_updated_at ON chats;
CREATE TRIGGER update_chats_updated_at
    BEFORE UPDATE ON chats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions to secondbrain user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO secondbrain;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO secondbrain;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO secondbrain;

-- Log successful completion
DO $$ 
BEGIN
    RAISE NOTICE 'SecondBrain database schema created successfully!';
    RAISE NOTICE 'Tables created: chats, messages, documents, document_chunks';
    RAISE NOTICE 'Extensions enabled: uuid-ossp, vector (pgvector)';
    RAISE NOTICE 'Ready for SecondBrain application!';
END $$;
