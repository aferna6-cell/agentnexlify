# Milestone 8 — Deployment readiness & live proof (2026-08-30)

**Verdict: MILESTONE 8 HOLD**

**Git SHA:** `b65d2f7ddad6e2fc8d5996077827f53f8d8c31ca` (branch tip; base main #711 `62ea09c2`)  
**Smoke tenant:** `7451537b-a694-4c31-83b0-1b804df3d757` (`AgentNexLiFy Smoke Test`)  
**Supabase project:** `pxserpybmajixqrmzaly`  
**Railway project:** `cheerful-freedom` / `22fbefe0-bd69-41c6-9896-e5f533473c60`  
**Railway environments:** **production only** (`5ee2962f-8355-4138-8865-6de80283a9ba`) — staging env **not created** (owner dashboard required; see `docs/ops/m8-staging-setup.md`)  
**Production API:** `https://agentnexlify-production.up.railway.app`  
**Staging API:** *not provisioned*

Companion machine JSON: `audits/artifacts/m8-deploy-proof-2026-08-30.json`  
Live smoke JSON: `audits/artifacts/m8-live-smoke-20260830T171155Z.json`  
RAG tenant proof: `audits/artifacts/m8-rag-smoke-tenant-proof.json`

No production feature flags were flipped. No secrets/tokens recorded.

---

## Capability matrix

| Capability | Live-proven? | Staging enabled? | Canary eligible? | Production eligible? | Blocker | Rollback |
|------------|--------------|------------------|------------------|----------------------|---------|----------|
| **RAG** | Partial — holdout + smoke-tenant retrieval/citations/abstention **pass**; Agent OS HTTP on staging deploy **not run** | **no** (no staging Railway env; prod flag unset) | **no** | **no** | Staging deploy missing; `RAG_ENABLED` not set on any Railway env | `RAG_ENABLED=0` |
| **CRM** | **no** (Action Executor / service-key path blocked). Offline eval **265/265**, unsafe **0**. DB-plane alone does not count. | **no** | **no** | **no** | No `SUPABASE_SERVICE_KEY` in agent env; no staging API | `CRM_ACTIONS_ENABLED=0` |
| **Calendar** | **no** | **no** | **no** | **no** | Zero `google_calendar` OAuth rows; no service key; no staging | `CALENDAR_ACTIONS_ENABLED=0` |
| **Gmail** | **no** | **no** | **no** | **no** | Zero `gmail` connector rows; no service key; no staging | `SEND_EMAIL_ENABLED=0` |

---

## Staging environment

| Check | Result |
|-------|--------|
| Separate non-prod Railway environment | **FAIL** — production only |
| Secrets injected via deploy env (not agent/commits) | **PASS policy** — OAuth MCP returns names only; runbook documents owner injection |
| Staging URL recorded | **blocked** — none exists |
| Owner runbook | `docs/ops/m8-staging-setup.md` |

## Smoke tenant

| Check | Result |
|-------|--------|
| Isolated tenant id | `7451537b-a694-4c31-83b0-1b804df3d757` |
| `clients` row restored | **pass** (`AgentNexLiFy Smoke Test`, synthetic only) |
| Synthetic leads only | **pass** (`*.invalid` emails) |
| No production customer used for smoke | **pass** |

## RAG

| Check | Result |
|-------|--------|
| Approved KB (services/prices/warranty/cancel/FAQs + out-of-scope) | **pass** — doc `a5dbe7dc-2277-4dd7-95ec-04a152bfff73` |
| Indexed `tenant_kb_chunks` active count | **6** (> 0) |
| Process `RAG_ENABLED=1`, `DEFAULT_MIN_SCORE=1.0` | **pass** |
| Holdout | Recall@1 **0.9017**; refusal **1.0**; unsupported **0**; leaks/injection **0** |
| Tenant citations + no-answer abstention | **pass** |
| Cross-tenant isolation on smoke corpus | **pass** (0 leaks) |
| Agent OS HTTP / staging flag | **not run** / **OFF** |

## CRM / Calendar / Gmail live Action Executor

All blocked at credential/provider gates (`scripts/m8_live_smoke.py` exit **3**):

1. Agent has no `SUPABASE_SERVICE_KEY` (Railway MCP names-only)
2. `tenant_integrations` has **no** `google_calendar` or `gmail` rows (global providers: only `os_inbound_bridges`)
3. No staging Railway environment to enable flags safely

Offline / unit / eval coverage remains green (see Regression).

## Feature flags (production Railway)

Variable **names** present on production `agentnexlify` do **not** include the M8 enable flags (defaults stay OFF in code). Staging flags must be set only after OAuth per runbook.

| Flag | Production | Staging |
|------|------------|---------|
| `RAG_ENABLED` | unset/OFF | not provisioned |
| `CRM_ACTIONS_ENABLED` | unset/OFF | not provisioned |
| `CALENDAR_ACTIONS_ENABLED` | unset/OFF | not provisioned |
| `SEND_EMAIL_ENABLED` | unset/OFF | not provisioned |

## Regression (this run)

| Gate | Result |
|------|--------|
| M6 action safety gate | **pass** — unsafe **0** / 59 labelled |
| M7 RAG holdout | **pass** — leaks/injection/unsupported **0** |
| M8 calendar/CRM gate | **pass** — **265/265**, unsafe **0** |
| `backend/tests/test_os_calendar_crm.py` + RAG + isolation | **31 passed** |
| `backend/tests/test_os_tool_executions.py` | **41 passed** |
| `npm run check:quick` | **pass** |

## Remaining concrete blockers (HOLD)

1. **Create Railway `staging` environment** (dashboard/CLI; agents cannot) and inject secrets there only.
2. **Owner OAuth:** connect harmless Google test account Calendar + Gmail to smoke tenant; verify integration rows.
3. **Inject service credentials** into the smoke runner environment (not commits) and re-run `scripts/m8_live_smoke.py` with `M8_SMOKE_API_BASE=<staging-url>` for CRM/Calendar/Gmail Action Executor proofs including `os_tool_executions` lifecycle + redrive.
4. Enable flags **staging-only** after (2), then capture provider object IDs / verification states in a new artifact.

Until those pass: **do not** enable production; **do not** start Milestone 9.
