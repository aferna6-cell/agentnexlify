-- 111: Phase 1 — missed_call_texts table + automations backfill + tenants.avg_ticket_override
-- Applied: 2026-04-22

-- ============================================================
-- 1. missed_call_texts
-- ============================================================
CREATE TABLE missed_call_texts (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    call_sid             text,
    sms_sid              text,
    from_phone           text,
    to_phone             text,
    template_id          text,
    status               text CHECK (status IN ('sent', 'failed', 'skipped')),
    created_at           timestamptz DEFAULT now(),
    converted_to_lead_id uuid REFERENCES leads(id)
);

-- RLS: service_role bypasses automatically; auth users see only their tenant rows
ALTER TABLE missed_call_texts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS missed_call_texts_tenant_isolation ON missed_call_texts;
CREATE POLICY missed_call_texts_tenant_isolation ON missed_call_texts
    FOR ALL USING (tenant_id = auth.uid());

CREATE INDEX idx_missed_call_texts_tenant_created
    ON missed_call_texts (tenant_id, created_at DESC);

-- ============================================================
-- 2. tenants.avg_ticket_override (Phase 2 attribution — cheap to land now)
-- ============================================================
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS avg_ticket_override decimal(10,2);

-- ============================================================
-- 3. Backfill: seed missed_call_textback automation row for existing tenants
-- ============================================================
INSERT INTO automations (tenant_id, type, name, is_enabled, config, runs_total)
SELECT
    id,
    'missed_call_textback',
    'Missed Call Text-Back',
    true,
    '{"mode": "hold", "hold_seconds": 60, "template_id": "default"}'::jsonb,
    0
FROM tenants
ON CONFLICT DO NOTHING;
