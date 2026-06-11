-- Migration 143: tenants.voice_ai_enabled (G3 phone calls).
--
-- Voice mode switch for inbound calls on a tenant's Twilio number:
--   false (default) -> voicemail mode: greeting + <Record>, transcription,
--     AI summary, lead creation, and an Agent OS callback-text draft
--     through the approval flow (Phase 1, missed-call recovery).
--   true  -> live AI answering: <Gather> speech loop with the tenant KB
--     (Phase 2). Plan-gated to professional/enterprise in
--     backend/routers/calls.py — the flag alone is not sufficient.

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS voice_ai_enabled BOOLEAN NOT NULL DEFAULT false;
