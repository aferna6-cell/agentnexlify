# Idea 04 — Connector Token Expiry Alerting (Step 9H Candidate)

**Evidence:**
- `backend/services/connector_registry.py` (b67710c, 314L): stores OAuth credentials via Fernet encryption. New services: Gmail connector, Google Calendar, HubSpot, M365 (deferred on UI but backend present).
- `migrations/176_sunset_plaintext_integration_tokens.sql`: will encrypt all integration tokens when INTEGRATIONS_ENC_KEY is provisioned.
- `run_102_mandate` item 4: "Connector token expiry (Idea 2): schema verified? gmail_integrations columns confirmed? If yes and GH queue unblocked: promote to run 102 winner."
- OAuth access tokens expire in 1 hour (Gmail). Refresh tokens expire in 6 months or on revocation. Without monitoring, expired connectors silently fail widget-triggered automations.
- `docs/dev-knowledge/bug-patterns.md` "Silent-green: Keys Koffee widget missing 5+ weeks undetected" — proven silent-failure risk pattern.

**Schema check (mandate item 4):**
- `migrations/007_google_calendar_integration.sql` and `109_tenant_integrations.sql` exist
- `migrations/176_sunset_plaintext_integration_tokens.sql` BLOCKED (pending INTEGRATIONS_ENC_KEY)
- Mandate says "schema verified? gmail_integrations columns confirmed?" — schema not fully verifiable while migration 176 is blocked. Promoting to winner DEFERRED until #536 unblocked.

**Idea:** Add Step 9H to nightly SKILL.md: query `tenant_integrations` for rows where `token_expires_at < now() + interval '7 days'`. Alert via GH issue if found.

**Expected impact:** Catches expired/expiring OAuth tokens before they silently fail user-facing automations. Same pattern as Steps 9B-9G.

**Effort:** S (query + alert, 1 step, ~15 lines)
**Confidence:** LOW — deferred (migration 176 blocked; schema verify incomplete)
**Mandate status:** PARKING LOT (promote when #536 unblocked and migration 176 applied)
