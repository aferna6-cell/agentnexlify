-- Migration 157: referral_clicks table
-- Tracks clicks on the "Powered by AgentNexLiFy" watermark in embedded widgets.
-- ref_tenant_id stores the widget's data-api-key (tenant identifier).

CREATE TABLE IF NOT EXISTS referral_clicks (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_tenant_id text NOT NULL,
    path        text,
    referrer    text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS referral_clicks_ref_tenant_id_idx
    ON referral_clicks (ref_tenant_id);

CREATE INDEX IF NOT EXISTS referral_clicks_created_at_idx
    ON referral_clicks (created_at DESC);
