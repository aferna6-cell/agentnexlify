-- 086: A/B Testing Tables
-- Support for multivariate marketing campaign testing with variant tracking

CREATE TABLE ab_tests (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    test_type TEXT NOT NULL CHECK (test_type IN ('subject_line', 'send_time', 'body_content', 'campaign_variant')),
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'completed', 'paused')),
    winner_variant_id UUID,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ab_test_variants (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ab_test_id UUID REFERENCES ab_tests(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    subject TEXT,
    body TEXT,
    send_time_override TIME,
    allocation_percent INTEGER DEFAULT 50 CHECK (allocation_percent >= 0 AND allocation_percent <= 100),
    is_winner BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ab_test_sends (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ab_test_id UUID REFERENCES ab_tests(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES ab_test_variants(id) ON DELETE CASCADE,
    campaign_send_id UUID REFERENCES campaign_sends(id) ON DELETE SET NULL,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    outcome TEXT CHECK (outcome IN ('sent', 'delivered', 'opened', 'clicked')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ab_tests_tenant ON ab_tests(tenant_id);
CREATE INDEX idx_ab_test_variants_test ON ab_test_variants(ab_test_id);
CREATE INDEX idx_ab_test_sends_test ON ab_test_sends(ab_test_id);
CREATE INDEX idx_ab_test_sends_variant ON ab_test_sends(variant_id);
