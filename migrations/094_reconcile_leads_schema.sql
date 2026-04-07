-- Migration 094: Reconcile leads schema with production reality
-- Date: 2026-04-07
-- Purpose: 8 columns existed in production but had no migration files.
--   These were added ad-hoc to Supabase and are required by active backend code.
--   Without this migration, any new environment (test/staging/demo) fails at runtime.

-- ── leads table: missing columns ──────────────────────────────

-- Lead temperature (hot/warm/cold) — used by lead scoring and frontend pipeline views
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_temperature TEXT
  CHECK (lead_temperature IN ('hot', 'warm', 'cold'));

-- Lead type (e.g. "buyer", "seller", "service_inquiry") — used by CRM categorization
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_type TEXT;

-- Must-haves (property preferences, service requirements, etc.)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS must_haves TEXT;

-- Pre-approved flag (mortgage pre-approval for real estate)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS pre_approved BOOLEAN DEFAULT false;

-- Conversation summary (AI-generated summary of the chat session)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS conversation_summary TEXT;

-- Next steps (AI-recommended follow-up actions)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS next_steps TEXT;

-- Appointment date (scheduled or suggested appointment timestamp)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS appointment_date TIMESTAMPTZ;

-- Updated at (last modification timestamp for the lead record)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- ── Indexes for commonly queried columns ──────────────────────

CREATE INDEX IF NOT EXISTS idx_leads_temperature ON leads(lead_temperature);
CREATE INDEX IF NOT EXISTS idx_leads_type ON leads(lead_type);
CREATE INDEX IF NOT EXISTS idx_leads_appointment_date ON leads(appointment_date) WHERE appointment_date IS NOT NULL;
