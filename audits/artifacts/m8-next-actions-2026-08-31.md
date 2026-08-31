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
