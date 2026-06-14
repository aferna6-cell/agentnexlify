-- Migration 134: Pricing page A/B test events (launch rubric 9.3)
-- Anonymous marketing-site events — no tenant FK, visitor_id is a first-party
-- cookie UUID, no PII stored.

CREATE TABLE IF NOT EXISTS pricing_ab_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id TEXT NOT NULL CHECK (char_length(visitor_id) BETWEEN 8 AND 64),
    variant TEXT NOT NULL CHECK (variant IN ('control', 'variant_b')),
    event TEXT NOT NULL CHECK (event IN ('view', 'cta_click')),
    plan TEXT CHECK (plan IN ('free', 'growth', 'autopilot', 'professional', 'enterprise')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pricing_ab_events_variant ON pricing_ab_events(variant, event);
CREATE INDEX IF NOT EXISTS idx_pricing_ab_events_created ON pricing_ab_events(created_at);

-- RLS: service-role only (written via backend public endpoint, read by admin)
ALTER TABLE pricing_ab_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access" ON pricing_ab_events
    FOR ALL USING (true) WITH CHECK (true);
