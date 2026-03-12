-- Migration 024: Add updated_at to appointments
-- The review request system (automation_engine.send_pending_review_requests)
-- uses updated_at to determine when an appointment status changed to "completed"
-- and whether enough time has passed to send a review request.

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
