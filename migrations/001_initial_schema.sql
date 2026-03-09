-- AgentNexLiFy Initial Schema
-- Migration: 001_initial_schema.sql

-- ============================================================
-- 1. tenants
-- ============================================================
CREATE TABLE tenants (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name                TEXT NOT NULL,
    business_type                TEXT CHECK (business_type IN ('plumbing','dental','realestate','legal','fitness','restaurant','other')),
    owner_email                  TEXT UNIQUE NOT NULL,
    phone                        TEXT,
    city                         TEXT,
    plan                         TEXT DEFAULT 'free' CHECK (plan IN ('free','growth','professional','enterprise')),
    plan_status                  TEXT DEFAULT 'active' CHECK (plan_status IN ('active','paused','cancelled')),
    stripe_customer_id           TEXT,
    stripe_subscription_id       TEXT,
    monthly_conversation_limit   INTEGER DEFAULT 50,
    conversations_used_this_month INTEGER DEFAULT 0,
    reset_date                   DATE,
    referral_code                TEXT UNIQUE,
    referred_by                  UUID REFERENCES tenants(id),
    referral_discount_pct        INTEGER DEFAULT 0,
    created_at                   TIMESTAMPTZ DEFAULT NOW(),
    updated_at                   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 2. widget_configs
-- ============================================================
CREATE TABLE widget_configs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    api_key          UUID UNIQUE DEFAULT gen_random_uuid(),
    bot_name         TEXT DEFAULT 'AI Assistant',
    primary_color    TEXT DEFAULT '#00BFFF',
    greeting_message TEXT,
    position         TEXT DEFAULT 'bottom-right',
    collect_name     BOOLEAN DEFAULT true,
    collect_email    BOOLEAN DEFAULT true,
    collect_phone    BOOLEAN DEFAULT true,
    show_watermark   BOOLEAN DEFAULT true,
    custom_css       TEXT,
    allowed_domains  TEXT[],
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 3. leads
-- ============================================================
CREATE TABLE leads (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name             TEXT,
    email            TEXT,
    phone            TEXT,
    service_interest TEXT,
    budget           TEXT,
    timeline         TEXT,
    lead_score       INTEGER DEFAULT 0,
    lead_stage       TEXT DEFAULT 'new',
    source           TEXT DEFAULT 'widget',
    conversation_id  UUID,
    notes            TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4. conversations
-- ============================================================
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_id      TEXT NOT NULL,
    messages        JSONB DEFAULT '[]'::jsonb,
    lead_id         UUID REFERENCES leads(id),
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 5. faq_entries
-- ============================================================
CREATE TABLE faq_entries (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    question   TEXT NOT NULL,
    answer     TEXT NOT NULL,
    category   TEXT,
    is_active  BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 6. automations
-- ============================================================
CREATE TABLE automations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type       TEXT NOT NULL CHECK (type IN ('missed_call_textback','review_request','drip_email','appt_reminder')),
    name       TEXT NOT NULL,
    is_enabled BOOLEAN DEFAULT false,
    config     JSONB DEFAULT '{}'::jsonb,
    runs_total INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Indexes on tenant_id
-- ============================================================
CREATE INDEX idx_widget_configs_tenant_id ON widget_configs(tenant_id);
CREATE INDEX idx_leads_tenant_id          ON leads(tenant_id);
CREATE INDEX idx_conversations_tenant_id  ON conversations(tenant_id);
CREATE INDEX idx_faq_entries_tenant_id    ON faq_entries(tenant_id);
CREATE INDEX idx_automations_tenant_id    ON automations(tenant_id);

-- ============================================================
-- Auto-update updated_at on tenants
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- Monthly conversation counter reset
-- Call via pg_cron or Supabase scheduled function on the 1st.
-- ============================================================
CREATE OR REPLACE FUNCTION reset_monthly_conversations()
RETURNS void AS $$
BEGIN
    UPDATE tenants
    SET conversations_used_this_month = 0,
        reset_date = (DATE_TRUNC('month', NOW()) + INTERVAL '1 month')::date
    WHERE reset_date IS NULL
       OR reset_date <= CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Enable Row Level Security (policies added later)
-- ============================================================
ALTER TABLE tenants        ENABLE ROW LEVEL SECURITY;
ALTER TABLE widget_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads          ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations  ENABLE ROW LEVEL SECURITY;
ALTER TABLE faq_entries    ENABLE ROW LEVEL SECURITY;
ALTER TABLE automations    ENABLE ROW LEVEL SECURITY;
