-- 081: Knowledge Base tables with pgvector
-- Enables semantic search over LLM-compiled wiki articles

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Compiled wiki articles with embeddings
CREATE TABLE kb_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    source_urls TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    word_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- HNSW index for cosine similarity search (works well at any scale)
CREATE INDEX kb_articles_embedding_idx ON kb_articles
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX kb_articles_category_idx ON kb_articles (category);

-- Raw source tracking and URL dedup
CREATE TABLE kb_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url TEXT UNIQUE,
    file_path TEXT NOT NULL,
    category TEXT NOT NULL,
    relevance_score INT,
    title TEXT,
    discovered_at TIMESTAMPTZ DEFAULT now(),
    compiled BOOLEAN DEFAULT false,
    compiled_at TIMESTAMPTZ
);

CREATE INDEX kb_sources_compiled_idx ON kb_sources (compiled) WHERE compiled = false;
