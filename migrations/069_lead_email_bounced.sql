-- Migration 069: Add email_bounced flag to leads table for bounce handling
-- Resend webhook sets this flag when an email bounces.
-- Automation engine and email sender skip leads with email_bounced = true.

ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_bounced BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_bounced_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_leads_email_bounced ON leads (email_bounced) WHERE email_bounced = TRUE;

COMMENT ON COLUMN leads.email_bounced IS 'Set to true when Resend reports a bounce for this lead email';
COMMENT ON COLUMN leads.email_bounced_at IS 'Timestamp when the bounce was recorded';
