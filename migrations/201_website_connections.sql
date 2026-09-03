-- 201_website_connections.sql
-- Website / chatbot connect v1 (GH #767).
-- One live website connection per tenant. "connected" is only written by
-- backend verification of this tenant's public widget key on the live HTML.
-- Never store CMS passwords or desktop-installer artifacts.
-- NOT applied to prod in this PR (no deploy / prod schema changes).

CREATE TABLE IF NOT EXISTS website_connections (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            uuid NOT NULL,
    website_url          text NOT NULL,
    platform             text NOT NULL DEFAULT 'unknown'
        CHECK (platform IN ('wordpress', 'wix', 'squarespace', 'godaddy', 'custom', 'unknown')),
    detected_platform    text
        CHECK (detected_platform IS NULL OR detected_platform IN ('wordpress', 'wix', 'squarespace', 'godaddy', 'custom', 'unknown')),
    platform_override    boolean NOT NULL DEFAULT false,
    status               text NOT NULL DEFAULT 'needs_action'
        CHECK (status IN ('needs_action', 'verifying', 'connected', 'failed')),
    verification_method  text,
    verification_detail  text,
    last_verified_at     timestamptz,
    last_checked_at      timestamptz,
    next_action_code     text,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id)
);

CREATE INDEX IF NOT EXISTS website_connections_tenant_status_idx
    ON website_connections (tenant_id, status);

ALTER TABLE website_connections ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS website_connections_service_role ON website_connections;
CREATE POLICY website_connections_service_role
    ON website_connections
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

COMMENT ON TABLE website_connections IS
    'Tenant website connect state. connected only after live HTML contains this tenant widget key.';

-- Rollback (manual, commented):
-- drop table if exists website_connections;
