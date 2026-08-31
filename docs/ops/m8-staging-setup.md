# Milestone 8 — Staging environment setup (owner runbook)

Coding agents **cannot** create Railway environments or read secret values via
OAuth MCP. This runbook is for a human owner with Railway + Google access.

Do **not** enable M8 flags on production. Do **not** use production customers.

## Identifiers (non-secret)

| Item | Value |
|------|-------|
| Railway project | `cheerful-freedom` / `22fbefe0-bd69-41c6-9896-e5f533473c60` |
| Staging environment | `5988ed51-6691-4497-825d-14fefff5f591` |
| Staging API | `https://agentnexlify-staging.up.railway.app` |
| Production environment | `5ee2962f-8355-4138-8865-6de80283a9ba` |
| Production API | `https://agentnexlify-production.up.railway.app` |
| Services | `agentnexlify` (`293f3d78-…`), `agent-service` (`1f6f4f55-…`) |
| Smoke tenant `client_id` | `7451537b-a694-4c31-83b0-1b804df3d757` |
| Smoke business | `AgentNexLiFy Smoke Test` |
| Staging Supabase project | `nohanoiugcbaxtxinttp` (**not** production) |
| Production Supabase project | `pxserpybmajixqrmzaly` |

## 1. Create Railway staging environment

1. Open https://railway.com/project/22fbefe0-bd69-41c6-9896-e5f533473c60
2. **Settings → Environments → + New Environment**
3. Name: `staging`
4. Prefer **Duplicate from production** when offered
5. Ensure both `agentnexlify` and `agent-service` deploy into staging
6. Generate a staging public domain for `agentnexlify` (record URL; never commit secrets)

CLI alternative (owner machine with Railway CLI authenticated):

```bash
railway environment new staging
# then copy/set variables from a secure store — do not paste secrets into chat/commits
```

## 2. Inject secrets via Railway Variables only

Copy required production secrets into **staging** from your password manager /
Railway dashboard (not from agent transcripts). Never put values in git,
artifacts, or issue comments.

On **staging `agentnexlify`**, set feature flags **after** OAuth (step 4):

| Variable | Staging value | Notes |
|----------|---------------|-------|
| `RAG_ENABLED` | `1` | Only after smoke KB indexed (`tenant_kb_chunks` active > 0) |
| `CRM_ACTIONS_ENABLED` | `1` | Smoke tenant only testing |
| `CALENDAR_ACTIONS_ENABLED` | `1` | After Google Calendar OAuth on smoke tenant |
| `SEND_EMAIL_ENABLED` | `1` | After Gmail OAuth on smoke tenant |
| (leave unset / `0` on production) | — | Production stays OFF |

Keep retrieval threshold frozen in code: `DEFAULT_MIN_SCORE=1.0`.

Record (non-secret) after create:

- staging environment id
- staging API base URL
- deployment ids

## 3. Smoke tenant

Tenant `7451537b-a694-4c31-83b0-1b804df3d757` holds synthetic leads + KB only.

- Owner email: `smoke-test@agentnexlify.invalid`
- Do not attach real customer data
- Confirm `tenant_kb_chunks` active count > 0 before enabling `RAG_ENABLED`

## 4. Connect Google Calendar + Gmail (normal product OAuth)

Sign in as the smoke-tenant owner in the **staging** dashboard/app and connect:

1. Google Calendar through the normal OAuth path  
2. Gmail through the normal OAuth path  

Verify rows exist (no token columns):

```sql
SELECT provider, enabled, last_sync_status
FROM tenant_integrations
WHERE client_id = '7451537b-a694-4c31-83b0-1b804df3d757'
  AND provider IN ('google_calendar', 'gmail');
```

Use a **harmless Google test account**. No external customers as attendees until
the external-attendee approval path is under test.

## 5. Run live smoke

On a machine that has staging secrets injected (never commit them):

```bash
export M8_SMOKE_AUTHORIZED=1
export M8_SMOKE_CLIENT_ID=7451537b-a694-4c31-83b0-1b804df3d757
export M8_SMOKE_ENV=staging
export M8_SMOKE_CONFIRM_ENV=staging
export M8_SMOKE_SUITES=rag,calendar,crm,gmail
export M8_SMOKE_API_BASE=https://<staging-agentnexlify-domain>
export M8_SMOKE_RAILWAY_PROJECT_ID=22fbefe0-bd69-41c6-9896-e5f533473c60
export M8_SMOKE_RAILWAY_ENVIRONMENT_ID=<staging-env-id>
export M8_SMOKE_RAILWAY_ENVIRONMENT_NAME=staging
# SUPABASE_URL + SUPABASE_SERVICE_KEY from staging vars (shell only)
# CALENDAR_ACTIONS_ENABLED=1 CRM_ACTIONS_ENABLED=1 SEND_EMAIL_ENABLED=1 as needed
python3 scripts/m8_live_smoke.py
```

Gmail external send additionally requires `M8_SMOKE_ALLOW_EXTERNAL_SEND=1` and
the manual approve procedure in `docs/milestone-6-gmail-proof.md`.

## 6. Rollback

Unset / set `=0` on staging (and never flip production):

- `RAG_ENABLED`
- `CRM_ACTIONS_ENABLED`
- `CALENDAR_ACTIONS_ENABLED`
- `SEND_EMAIL_ENABLED`

## Blockers until owner completes this

1. ~~Railway staging environment does not exist (production only today)~~ **done** — staging env + API live
2. **Inject real staging Supabase `service_role` JWT** into Railway staging `SUPABASE_SERVICE_KEY` and agent secret `STAGING_SUPABASE_SERVICE_ROLE_KEY` (anon-as-service-key breaks login/automation after RLS re-enable). Helpers: `python3 scripts/m8_wire_staging_service_key.py` then Railway redeploy; gate: `python3 scripts/m8_verify_staging_step3.py`
3. Add Google OAuth staging redirect URIs (Calendar + Gmail callbacks on `agentnexlify-staging.up.railway.app`)
4. Connect Calendar + Gmail OAuth on smoke tenant in the staging app (zero `google_calendar` / `gmail` rows until then)
5. Re-run `M8_SMOKE_SUITES=isolation,rag,crm,calendar,gmail,agent_os_e2e` then M6/M7/M8 regression gates

Note: agent environments cannot read Railway/Supabase secret values via OAuth MCP — owner must paste `STAGING_SUPABASE_SERVICE_ROLE_KEY` into the trusted smoke environment.
