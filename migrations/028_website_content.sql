-- Migration 028: Website content crawling
-- Adds website_url to tenants and creates website_content table for crawl results

-- Add website_url to tenants
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS website_url TEXT;

-- Create website_content table
CREATE TABLE IF NOT EXISTS website_content (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    pages_json JSONB DEFAULT '[]'::jsonb,
    extracted_text TEXT,
    crawl_status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    pages_found INTEGER DEFAULT 0,
    crawled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for tenant lookup
CREATE INDEX IF NOT EXISTS idx_website_content_tenant ON website_content(tenant_id);

-- RLS
ALTER TABLE website_content ENABLE ROW LEVEL SECURITY;

CREATE POLICY website_content_tenant_policy ON website_content
    FOR ALL USING (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'sub');
