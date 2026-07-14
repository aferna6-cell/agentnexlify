-- Migration 164: dedicated tenants.twilio_number for provisioned AI lines
--
-- Voice G3 Phase 2 (audits/audit-voice-g3-scope-2026-07-09.md gap #5).
-- The number-provisioning flow (backend/routers/phone.py) stored the purchased
-- Twilio number in tenants.notification_phone, which is ALSO the owner's own
-- alert phone (missed-call SMS notify, calls.py). Two real defects followed:
--   1. Owner alerts would SMS the tenant's own AI line after provisioning.
--   2. Tenants with a notification_phone already set (all real tenants) got a
--      409 from /provision and could never buy a number.
--
-- twilio_number holds the provisioned inbound AI line, E.164. Partial unique
-- index doubles as the exact-match routing lookup for /voice/incoming, which
-- replaces the limit(50) suffix scan in calls.py (suffix match on
-- notification_phone stays as the legacy fallback for existing tenants).

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS twilio_number TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS tenants_twilio_number_uniq
    ON tenants (twilio_number)
    WHERE twilio_number IS NOT NULL;
