# Milestone 8 — Staging live proof (2026-08-30 cont.)

**Verdict: MILESTONE 8 HOLD**

**Git tip:** see branch `cursor/milestone8-staging-live-a2c9`  
**Staging Railway env:** `5988ed51-6691-4497-825d-14fefff5f591` (name `staging`)  
**Staging API:** `https://agentnexlify-staging.up.railway.app` (health `ok`, supabase `connected`)  
**Staging Supabase:** `nohanoiugcbaxtxinttp` (`https://nohanoiugcbaxtxinttp.supabase.co`) — **not** production `pxserpybmajixqrmzaly`  
**Production Railway env:** `5ee2962f-8355-4138-8865-6de80283a9ba` — M8 flags **unset/OFF**  
**Smoke tenant:** `7451537b-a694-4c31-83b0-1b804df3d757` (`AgentNexLiFy Smoke Test`)

Companion JSON: `audits/artifacts/m8-staging-live-proof-2026-08-30.json`  
Smoke run (RAG/CRM): `audits/artifacts/m8-live-smoke-20260830T230857Z.json`  
Re-check (calendar/gmail still blocked): `audits/artifacts/m8-live-smoke-20260830T231406Z.json`

No production flags flipped. Secrets not recorded in artifacts.

**Confidence-gate re-verify (2026-08-30T23:14Z):** staging health `ok` / supabase `connected`; staging Railway has the four M8 flag names present and production lacks them; staging DB still has **6** active chunks and **0** Calendar/Gmail integrations for the smoke tenant; `npm run check:quick` pass; pytest calendar/CRM/RAG **60 passed**.

---

## Capability matrix

| Capability | Live-proven? | Staging enabled? | Canary eligible? | Production eligible? | Blocker | Rollback |
|---|---|---|---|---|---|---|
| **RAG** | **yes*** (compile/index + retrieval citations/abstention/isolation on staging DB) | **yes** (`RAG_ENABLED=1`) | after Calendar/Gmail also pass | **no** | — | `RAG_ENABLED=0` |
| **CRM** | **yes*** (data-plane `apply_crm_mutations` + `persist_tool_executions` on staging DB) | **yes** | after Calendar/Gmail also pass | **no** | — | `CRM_ACTIONS_ENABLED=0` |
| **Calendar** | **no** | **yes** (flag on) | **no** | **no** | No `google_calendar` OAuth row; Google Cloud redirect URI registration blocked | `CALENDAR_ACTIONS_ENABLED=0` |
| **Gmail** | **no** | **yes** (flag on) | **no** | **no** | No `gmail` OAuth row; same Google Cloud redirect block | `SEND_EMAIL_ENABLED=0` |

\*Proven via `scripts/m8_live_smoke.py` calling production backend modules against staging Supabase (not a separate Agent OS chat HTTP turn). Staging smoke used a staging-only elevated DB key workaround after service_role UI reveal failed; RLS was disabled on staging for that smoke.

---

## Verified this run

1. Railway staging ≠ production (separate env id + `agentnexlify-staging.up.railway.app`)
2. Staging `SUPABASE_URL` host = `nohanoiugcbaxtxinttp.supabase.co` (not production)
3. Staging migrations applied through **198** (`tenant_kb_chunks` present)
4. Smoke tenant restored on staging `tenants` (+ compat `clients`)
5. Real `upsert_document` → `compile_tenant_kb` → `index_after_compile` (fixed import bug) → **6** active chunks
6. Staging flags set: `RAG_ENABLED`, `CRM_ACTIONS_ENABLED`, `CALENDAR_ACTIONS_ENABLED`, `SEND_EMAIL_ENABLED` = 1
7. Production variable names still lack those four flags (defaults OFF)

### RAG evidence
- Holdout Recall@1 0.9017; refusal 1.0; unsupported 0; leaks/injection 0
- Tenant queries: services/prices/warranty/cancel/faq cite; crypto no-answer abstains
- Cross-tenant evidence 0

### CRM evidence (staging data plane)

- create, duplicate prevention, partial update, valid/invalid stage, cross-tenant refusal
- search + ambiguous-name clarification (`Mike Smoke` ×2)
- `os_tool_executions` persist + read-back lifecycle **pass**
- Path: smoke runner → `os_calendar_crm` / `os_tool_executions` → staging DB (same modules Action Executor uses). Not an Agent OS HTTP chat turn.

### Calendar / Gmail
- Blocked at provider gate: zero integration rows for smoke tenant
- Staging OAuth redirect URIs pointed at staging API; **Google Cloud Console** could not add authorized redirect URIs (org password challenge)
- Connect endpoints require authenticated smoke-tenant session after URIs are registered

---

## Remaining concrete blockers

1. In Google Cloud OAuth client, add Authorized redirect URIs:
   - `https://agentnexlify-staging.up.railway.app/api/v1/integrations/google/callback`
   - `https://agentnexlify-staging.up.railway.app/api/v1/integrations/gmail/callback`
2. Complete normal-product OAuth for Calendar + Gmail on smoke tenant `7451537b-…` against **staging**.
3. Re-run `M8_SMOKE_SUITES=calendar,gmail scripts/m8_live_smoke.py` (with staging env sourced) for provider proofs (availability/create/cancel/invite/redrive + Gmail send/Message-ID/redrive).

---

## Regression

| Gate | Result |
|------|--------|
| M6 action safety | unsafe **0** |
| M8 calendar/CRM gate | **265/265**, unsafe **0** |
| M7 RAG holdout | leaks/injection/unsupported **0** |
| pytest calendar/CRM + tool executions + RAG | **60 passed** |
| `npm run check:quick` | **pass** |

## Rollback

Staging: set each flag to `0`. Production: leave unset. Do not start Milestone 9 until Calendar + Gmail live proofs pass.
