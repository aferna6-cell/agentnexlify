# Runbook — Zapier CRM Export Failures

Operational playbook for the Zapier CRM-export integration
(`backend/routers/zapier.py`, `backend/services/api_key_auth.py`,
`backend/services/api_key_limiter.py`). The polling endpoint is
`GET /api/zapier/leads/new`; dashboard key management is under
`/api/zapier/keys`.

Related: KB `knowledge-base/wiki/integrations/zapier.md`.

## Symptom → cause → action

### Rate limit tripped (429)
- **Symptom:** a tenant's Zap shows 429 responses; leads lag or stop until the
  next minute bucket.
- **Cause:** the API key exceeded its per-minute request budget — usually a
  misconfigured Zap polling far more often than once a minute, or many Zaps
  sharing one key.
- **Action:** confirm the Zap's polling interval is the default (1/min). Split
  high-volume automations across separate keys (each key has its own budget).
  The limiter is per-process and fails open, so a 429 is a guardrail, not data
  loss — Zapier retries next interval. If a legitimate tenant genuinely needs a
  higher budget, raise `rate_limit_rpm` on that key row.

### Suspected key leak (rotation procedure)
- **Symptom:** a key appears in a shared Zap export, a screenshot, a support
  thread, or logs; unexpected polling from an unknown source.
- **Cause:** the single-view raw key was copied somewhere it should not be.
- **Action:** rotate immediately. In **Settings → Integrations → Zapier**,
  **Revoke** the exposed key (revocation sets `revoked_at` and the key stops
  authenticating instantly — a soft-delete, not a hard delete). Then **Generate**
  a new key, update the Zap's authentication with the new key, and confirm the
  trigger tests green. Because keys are stored only as a bcrypt hash + prefix,
  the platform cannot re-display the old key; rotation is the only remedy and it
  is complete the moment the old key is revoked.

### Zapier app review rejection (pre-publish)
- **Symptom:** the Zapier CLI app submission (issue #61) is rejected in review.
- **Cause:** review feedback on auth copy, trigger sample data, or field
  descriptions — common on first submission.
- **Action:** address the reviewer's specific notes in the Zapier CLI app
  definition (auth label/help text, trigger `perform` sample, output field
  labels), bump the app version, and resubmit. This does not affect existing
  tenants: API-key auth against `/api/zapier/leads/new` works independently of
  the public app listing. Track under issue #61.

### v1 → v2 schema migration
- **Symptom:** a breaking change to the lead payload is needed (renamed field,
  changed `areas_of_interest` delimiter, nested object).
- **Cause:** product evolution beyond the pinned v1 flat schema.
- **Action:** never mutate `/api/zapier/leads/new` (v1) in place — a live Zap
  maps against the current fields and a mutation breaks every tenant's Zap.
  Ship the change as a new `/api/zapier/v2/leads/new` endpoint, publish a v2
  trigger in the Zapier app, and let tenants migrate on their own schedule.
  Keep v1 serving until usage drains. This is the same "v1 pinned" discipline
  documented in the KB article.

## Escalation
Most Zapier issues are tenant-side (misconfigured Zap, leaked key) and resolve
with a re-test or a key rotation, not a code change. Check the tenant's key
state (`revoked_at`, `last_used_at`) and plan/subscription status first — a
402 means the tenant dropped below the premium tier or their subscription
cancelled, which correctly cuts Zapier access (GH #107).
