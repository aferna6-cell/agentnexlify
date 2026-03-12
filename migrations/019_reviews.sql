-- Migration 019: Reviews table for Reputation Manager module
-- Stores reviews from Google Business Profile and other platforms

CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    platform TEXT NOT NULL DEFAULT 'google',  -- google, yelp, facebook
    author_name TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    review_date TIMESTAMPTZ,
    ai_draft_response TEXT,
    owner_response TEXT,
    responded BOOLEAN NOT NULL DEFAULT FALSE,
    external_review_id TEXT,  -- ID from the platform for dedup
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_tenant ON reviews (tenant_id);
CREATE INDEX IF NOT EXISTS idx_reviews_tenant_platform ON reviews (tenant_id, platform);
CREATE INDEX IF NOT EXISTS idx_reviews_tenant_rating ON reviews (tenant_id, rating);

-- RLS
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
CREATE POLICY reviews_service_role ON reviews FOR ALL USING (true) WITH CHECK (true);
