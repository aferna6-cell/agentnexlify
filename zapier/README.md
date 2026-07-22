# AgentNexLiFy Zapier Integration (#61)

Zapier CLI app exposing a **New Lead** polling trigger backed by the
tier-gated API-key endpoint `GET /api/zapier/leads/new`
(`backend/routers/zapier.py`). Tenants generate a key in the dashboard
(Settings → Integrations → Zapier) and paste it into Zapier.

See also: `knowledge-base/wiki/integrations/zapier.md`,
`docs/runbooks/zapier-failures.md`.

## What's in this directory (implemented, syntax-verified)

- `index.js` — app definition: custom API-key auth + `beforeRequest` that adds
  the `X-API-Key` header + the `new_lead` trigger.
- `authentication.js` — `type: 'custom'` API-key field; auth test hits
  `/api/zapier/leads/new?since=1970-01-01&limit=1` (200/empty = valid key).
- `triggers/new_lead.js` — polling trigger; `perform` calls
  `/api/zapier/leads/new?since=<rolling>&limit=50`; sample + typed output fields
  matching the flat v1 schema `{id, client_id, name, email, phone,
  areas_of_interest, status, created_at}`.
- `constants.js` — base URL (env-overridable) + lookback/limit.
- `package.json` — `zapier-platform-core` dependency.

Base URL defaults to production Railway; override with `AGENTNEXLIFY_BASE_URL`
for staging/local.

## Remaining steps — OWNER (external, cannot run in CI/agent env)

These require a Zapier developer account and the Zapier CLI logged in; they are
outside this repo's automatable surface. Track under issue #61.

1. Register a Zapier developer account (Aidan); store credentials in 1Password.
2. `npm install` in this directory, then `npm install -g zapier-platform-cli`.
3. `zapier login` and `zapier register "AgentNexLiFy"` (or link this dir with
   `zapier init . --template minimal` scaffolding already provided here).
4. `zapier validate` — must pass.
5. `zapier test` — auth test + trigger perform against a real key.
6. Upload logo + screenshots in the Zapier developer dashboard.
7. `zapier push` — private beta; invite 5 beta testers.
8. After beta: `zapier promote <version>` to submit for public review
   (2–4 week Zapier review per spec).
9. After promotion, set the published deep-link
   (`https://zapier.com/apps/agentnexlify/integrations/<XYZ>`) as
   `ZAPIER_APP_URL` in `frontend/src/pages/IntegrationsZapierPage.jsx` — the
   dashboard "Connect to Zapier" button (#60) activates automatically once set.

## Local sanity (no Zapier account needed)

`node --check` on each `.js` file confirms syntax. Full `zapier validate`/`test`
requires `zapier-platform-core` installed and a Zapier login (owner step above).
