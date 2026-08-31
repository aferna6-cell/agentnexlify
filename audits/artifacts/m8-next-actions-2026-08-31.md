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

## Merge with main (2026-08-31)

- Fetched `origin/main`; branch is **current** (merge commit `e35a23d5`).
- **One simple conflict** resolved in `docs/ops/m8-staging-setup.md` (blocker wording + deduped numbered list from main).
- Auto-merged: `backend/services/m8_action_flags.py`, nightly review docs.
- PR #716 CI: **all green**.

## Step-3 re-check (2026-08-31T11:23Z)

```
PASS /health ok
PASS anon tenant_kb_chunks []
FAIL local service key role is not service_role
FAIL service_role smoke chunks n=0
FAIL smoke login http=401
```

`STAGING_SUPABASE_SERVICE_ROLE_KEY` still **unset** in agent environment.

## Confidence gate (2026-08-31T00:56Z)

**Score for M8 COMPLETE / production-ready: 42% — KEEP WORKING (owner secrets required).**

**Score for HOLD package accuracy (this PR’s claims): 88%.**

### Verified again
- Staging RLS still **140 on / 0 off**
- Anon REST: chunks/leads/tenants → `[]`
- Local service key JWT role still **anon**
- Calendar/Gmail integrations still **0**
- `service_role_gate` correctly **blocked**
- Staging login still **401** (expected until Railway has real service_role)
- `check:quick` + pytest 60 passed on prior turn; smoke script compiles

### Uncertainties blocking ≥90% COMPLETE
1. No real staging `service_role` JWT available (Reveal UI broken; masked `••••` paste rejected; Railway agent cannot read secret values)
2. Google OAuth redirect URIs still blocked by Clemson org password
3. Agent OS E2E + calendar/gmail live proofs not runnable until (1)+(2)
4. Staging app is degraded for tenant-scoped jobs until Railway `SUPABASE_SERVICE_KEY` is fixed

Staff engineer would approve the HOLD and the RLS move, and would **not** approve COMPLETE while (1)–(3) remain.

## Immediate owner checklist

1. Reveal staging Supabase **service_role** JWT (must start with `eyJ`, role claim `service_role`) → set Railway staging `SUPABASE_SERVICE_KEY` + `.env.staging` / `STAGING_SUPABASE_SERVICE_ROLE_KEY`
2. Add Google redirect URIs (exact):
   - `https://agentnexlify-staging.up.railway.app/api/v1/integrations/google/callback`
   - `https://agentnexlify-staging.up.railway.app/api/v1/integrations/gmail/callback`
3. Log into staging as `smoke-test@agentnexlify.invalid` and connect harmless Google Calendar + Gmail
4. Ask Cursor to re-run `isolation,rag,crm,calendar,gmail,agent_os_e2e` + M6/M7/M8 gates

## Confidence gate recheck (2026-08-31T01:52Z)

**COMPLETE / production-ready confidence: still 42% (<90%).**

Re-verified: service key role=`anon`; login 401; integrations 0; isolation anon checks pass; `service_role_gate` blocked.
Smoke artifact: `audits/artifacts/m8-live-smoke-20260831T015206Z.json`.
Supabase Reveal / DevTools extraction still fail; owner must paste `STAGING_SUPABASE_SERVICE_ROLE_KEY`.
