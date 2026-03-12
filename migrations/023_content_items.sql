-- Migration 023: Content Studio — content_items table
-- Stores source content that tenants input for AI repurposing into
-- platform-specific posts (LinkedIn, Facebook, Instagram, GBP, email, X).

CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'text',  -- 'text', 'description', 'file'
    source_content TEXT NOT NULL,
    platform_versions JSONB DEFAULT '{}'::jsonb,  -- keyed by platform name
    status TEXT NOT NULL DEFAULT 'draft',  -- 'draft', 'generated', 'scheduled', 'published'
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_items_tenant ON content_items(tenant_id);
CREATE INDEX IF NOT EXISTS idx_content_items_status ON content_items(tenant_id, status);

ALTER TABLE content_items ENABLE ROW LEVEL SECURITY;
