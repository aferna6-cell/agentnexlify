-- Migration 021: Add unsubscribe tracking to leads
-- CAN-SPAM compliance: every outreach email must include an unsubscribe link.
-- When a lead unsubscribes, no further automated emails/SMS are sent.

ALTER TABLE leads ADD COLUMN IF NOT EXISTS unsubscribed BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS unsubscribed_at TIMESTAMPTZ;

-- Index for quick filtering of unsubscribed leads in automation queries
CREATE INDEX IF NOT EXISTS idx_leads_unsubscribed ON leads (unsubscribed) WHERE unsubscribed = TRUE;
