-- 088: Campaign Analytics Aggregates
-- Pre-computed daily/weekly campaign metrics for fast dashboard queries

CREATE TABLE campaign_analytics_aggregates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_type TEXT CHECK (period_type IN ('daily', 'weekly')),
    total_sent INTEGER DEFAULT 0,
    total_delivered INTEGER DEFAULT 0,
    total_opened INTEGER DEFAULT 0,
    total_clicked INTEGER DEFAULT 0,
    total_bounced INTEGER DEFAULT 0,
    unique_opens INTEGER DEFAULT 0,
    unique_clicks INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(campaign_id, period_start, period_type)
);

CREATE INDEX idx_campaign_analytics_agg_tenant ON campaign_analytics_aggregates(tenant_id);
CREATE INDEX idx_campaign_analytics_agg_campaign ON campaign_analytics_aggregates(campaign_id);
