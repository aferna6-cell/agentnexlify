-- Migration 045: Local SEO Tools — profile scores + keyword suggestions
-- Tracks GBP profile completeness and local keyword recommendations.

CREATE TABLE IF NOT EXISTS seo_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    completeness_score INTEGER NOT NULL DEFAULT 0,
    missing_fields JSONB DEFAULT '[]'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    keyword_suggestions JSONB DEFAULT '[]'::jsonb,
    last_analyzed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_seo_profiles_tenant ON seo_profiles(tenant_id);

ALTER TABLE seo_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on seo_profiles" ON seo_profiles
    FOR ALL USING (current_setting('role', true) = 'service_role');
