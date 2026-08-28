-- 194: Voice receptionist add-on (+$49.99/mo) — per-tenant subscription flag.
-- Lets a chatbot-plan tenant buy live AI phone answering without upgrading to
-- agent_os. Set/cleared by the Stripe webhook on addon subscription events
-- (backend/routers/billing.py, metadata.addon = 'voice').
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS voice_addon_active BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN tenants.voice_addon_active IS
    'Live AI voice add-on subscription active (Stripe addon=voice). Grants the live AI call loop regardless of plan tier; voice_ai_enabled must also be on.';
