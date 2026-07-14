-- Migration 172: lead attribution (#T2)
--
-- Closed-loop attribution so a tenant can see which channel/campaign drove a
-- booked appointment. The widget captures utm_* params + referrer + a source
-- label and sends them with the lead; this column stores that provenance.
-- `leads` uses client_id (NOT tenant_id) -- see schema-discipline.md. No new
-- tenant column; attribution describes the lead itself.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS attribution jsonb;
