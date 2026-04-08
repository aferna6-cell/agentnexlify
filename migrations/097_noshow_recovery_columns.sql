-- Migration 097: Add no-show recovery tracking columns to appointments
-- These columns track when recovery outreach was sent to no-show customers
-- to prevent duplicate messages and enable follow-up sequences.

ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS noshow_recovery_sent_at timestamptz,
  ADD COLUMN IF NOT EXISTS noshow_followup_sent_at timestamptz;

-- Index for the no-show recovery query:
-- SELECT ... FROM appointments WHERE status='no_show' AND noshow_recovery_sent_at IS NULL
CREATE INDEX IF NOT EXISTS idx_appointments_noshow_recovery
  ON appointments (status, noshow_recovery_sent_at)
  WHERE status = 'no_show';
