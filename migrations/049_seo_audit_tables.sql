-- Migration 049: SEO Audit, GEO Scores, and Keyword Ranking tables
-- Supports comprehensive website SEO auditing, GEO visibility scoring,
-- and keyword tracking features.

-- SEO Audit results
CREATE TABLE IF NOT EXISTS seo_audits (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    overall_score INTEGER NOT NULL DEFAULT 0,
    categories JSONB DEFAULT '{}'::jsonb,
    critical_issues JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    passed_checks JSONB DEFAULT '[]'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    pages_analyzed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_seo_audits_tenant ON seo_audits(tenant_id);
CREATE INDEX IF NOT EXISTS idx_seo_audits_created ON seo_audits(tenant_id, created_at DESC);

ALTER TABLE seo_audits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on seo_audits" ON seo_audits
    FOR ALL USING (current_setting('role', true) = 'service_role');

-- GEO (Generative Engine Optimization) visibility scores
CREATE TABLE IF NOT EXISTS geo_scores (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    overall_score INTEGER NOT NULL DEFAULT 0,
    platform_scores JSONB DEFAULT '{}'::jsonb,
    visibility_factors JSONB DEFAULT '[]'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    business_name TEXT,
    business_type TEXT,
    city TEXT,
    website_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_geo_scores_tenant ON geo_scores(tenant_id);
CREATE INDEX IF NOT EXISTS idx_geo_scores_created ON geo_scores(tenant_id, created_at DESC);

ALTER TABLE geo_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on geo_scores" ON geo_scores
    FOR ALL USING (current_setting('role', true) = 'service_role');

-- Keyword tracking and rankings
CREATE TABLE IF NOT EXISTS keyword_rankings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    difficulty_score INTEGER DEFAULT 50,
    estimated_position TEXT,
    search_volume_estimate TEXT,
    recommendations JSONB DEFAULT '[]'::jsonb,
    last_analyzed_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_keyword_rankings_tenant ON keyword_rankings(tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_keyword_rankings_unique ON keyword_rankings(tenant_id, keyword);

ALTER TABLE keyword_rankings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on keyword_rankings" ON keyword_rankings
    FOR ALL USING (current_setting('role', true) = 'service_role');
