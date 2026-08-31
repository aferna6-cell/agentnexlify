# Milestone 8 — Next-actions progress (2026-08-31)

**Verdict: still MILESTONE 8 HOLD** (not COMPLETE)

## 1) Re-enable RLS on staging — DONE (partial proof)

- Applied staging migration `reenable_rls_match_production_posture`.
- **140/140** public tables now have `relrowsecurity=true` (was all false).
- Backfilled missing policies: `service_all_leads`, `service_all_clients`, `service_all_messages`, `service_role_full_access` (tenant_integrations), `service_all_conversations`.
- Anon REST proof (normal publishable/anon key):
  - `tenant_kb_chunks` → `[]`
  - `leads` → `[]`
  - Artifact: `audits/artifacts/m8-live-smoke-20260831T005331Z.json` (`isolation.anon_cannot_read_*` **pass**)

### Blocker to finish isolation with “normal staging credentials”

Local `.env.staging` and (observed behavior of) Railway staging still use an **anon** JWT labeled as `SUPABASE_SERVICE_KEY`. After RLS re-enable:

- Local smoke `service_role_gate` → **blocked** (role claim `anon`).
- Staging `/api/v1/auth/login` → **401** for smoke owner (tenant row invisible to anon under RLS).
- Staging logs: `send_daily_briefings: failed to query tenants`.

**Owner action required:** paste staging project `nohanoiugcbaxtxinttp` **service_role** secret into:

1. Railway staging `agentnexlify` → `SUPABASE_SERVICE_KEY` (+ keep `SUPABASE_KEY` = anon)
2. Agent workspace secret `STAGING_SUPABASE_SERVICE_ROLE_KEY` / `/workspace/.env.staging`

Then re-run:

```bash
set -a && source /workspace/.env.staging && set +a
M8_SMOKE_SUITES=isolation,crm,rag PYTHONPATH=/workspace \
  python3 scripts/m8_live_smoke.py
```

Smoke tenant login is prepared (password in gitignored `.env.staging` only; plan=`agent_os`).

## 2–4) Google OAuth redirects + connect Calendar/Gmail — BLOCKED

- Redirect URIs still need to be added to the existing Google OAuth Web client (Clemson org password challenge blocks agent).
- Staging DB: **0** `integrations` / `tenant_integrations` rows for smoke tenant Calendar/Gmail.

## 5) `M8_SMOKE_SUITES=calendar,gmail` — BLOCKED

Blocked on service_role + OAuth connect (provider gates).

## 6) True Agent OS E2E suite — IMPLEMENTED, not yet live-proven

`scripts/m8_live_smoke.py` adds:

- `isolation` suite
- `agent_os_e2e` suite: staging login → `POST /api/v1/os/threads` → `POST .../messages` → poll `/api/v1/os/tool-executions`
- Hard fail-closed if service key JWT role ≠ `service_role`

Live run today: `agent_os_e2e.login` **blocked** (staging cannot read tenants until service_role is on Railway).

## 7) COMPLETE criteria — not met

Do **not** start Milestone 9. Production M8 flags remain unset/OFF.

## Immediate owner checklist

1. Reveal staging Supabase **service_role** → set Railway staging + `.env.staging`
2. Add Google redirect URIs (exact):
   - `https://agentnexlify-staging.up.railway.app/api/v1/integrations/google/callback`
   - `https://agentnexlify-staging.up.railway.app/api/v1/integrations/gmail/callback`
3. Log into staging as `smoke-test@agentnexlify.invalid` and connect harmless Google Calendar + Gmail
4. Ask Cursor to re-run `isolation,rag,crm,calendar,gmail,agent_os_e2e` + M6/M7/M8 gates
