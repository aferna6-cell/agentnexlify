# Milestone 8 live-proof evidence — 2026-08-30

**Branch:** `cursor/milestone8-live-proof-a2c9`  
**Base git SHA (main @ #710):** `a36f97afe68279355f83d41c9d0ef020b2da5473`  
**Environment:** agent cloud VM + production Supabase project `pxserpybmajixqrmzaly` (read/discovery)  
**Smoke tenant (non-sensitive id):** `7451537b-a694-4c31-83b0-1b804df3d757` (`AgentNexLiFy Smoke Test`)  
**Railway:** project `cheerful-freedom` has **production only** (no separate staging env)

Companion machine JSON: `audits/artifacts/m8-live-smoke-20260830T165228Z.json`

## Authorization / runner

| Check | Result |
|-------|--------|
| Unset auth → refuse | **pass** (exit 2) |
| Real runner | `scripts/m8_live_smoke.py` (wrapper: `scripts/m8_controlled_smoke.py`) |
| Requires | `M8_SMOKE_AUTHORIZED=1`, `M8_SMOKE_CLIENT_ID`, `M8_SMOKE_ENV=staging`, `M8_SMOKE_CONFIRM_ENV=staging` |
| Exit 0 on guard-only | **no** — credentials/provider required for Calendar/CRM/Gmail |

## RAG

| Item | Result |
|------|--------|
| Process soak `RAG_ENABLED=1`, `DEFAULT_MIN_SCORE=1.0` | **pass** (holdout) |
| Recall@1 | 0.9017 |
| Correct refusal | 1.0 |
| False refusal | 0 |
| Unsupported claims | 0 |
| Cross-tenant leaks | 0 |
| Prompt-injection failures | 0 |
| Railway `RAG_ENABLED` | **unchanged OFF** (OAuth app cannot set vars; only production env exists) |
| Live `tenant_kb_chunks` active | **0 rows** — live tenant RAG would abstain until compile/index |
| Staging eligible? | Holdout yes; live tenant soak **blocked** (empty chunks + no staging deploy) |
| Production eligible? | **no** |

## Calendar

| Item | Result |
|------|--------|
| Live smoke | **blocked** |
| Blocker 1 | Agent env has no `SUPABASE_SERVICE_KEY` (Railway MCP returns names only) |
| Blocker 2 | DB has **zero** `google_calendar` / `gmail` rows in `tenant_integrations` |
| Availability / create / cancel / invite / redrive | **not executed** (no provider) |
| Idempotency claim | Unchanged: best-effort fingerprint + claim gate — **not** Google exactly-once |

## CRM

| Item | Result |
|------|--------|
| Action Executor path (`apply_crm_mutations` via service client) | **blocked** (no service key in agent env) |
| DB-plane staging mutations on smoke tenant (Supabase MCP) | **partial pass** (see below) |
| Offline/unit Action Executor CRM | **pass** (prior #710 + eval 265/265) |

### DB-plane smoke tenant evidence (not Action Executor HTTP)

| Step | Evidence | Result |
|------|----------|--------|
| Create | lead `1b567711-eb90-4fc8-aad9-1042ae12fab5` on smoke `client_id` | pass |
| Partial update | phone → `555-9999`; name/email unchanged on read-back | pass |
| Duplicate email lookup | exactly 1 row for `m8-smoke-ada@example.invalid` | pass (dedupe input for app layer) |
| Ambiguous name | 2× `Mike Smoke` on smoke tenant | pass (clarification input) |
| Valid stage | `status=contacted` read-back | pass |
| Cross-tenant filter | update with wrong `client_id` → 0 rows; other tenant email leak count 0 | pass |
| Invalid stage / `os_tool_executions` audit lifecycle | **not** live-proven on Action Executor path | blocked |
| App-layer invalid stage refuse | covered by unit tests | pass (offline) |

## Gmail

| Item | Result |
|------|--------|
| Live proof | **blocked** |
| Blockers | No service key in agent env; **no gmail** connector rows in DB; Railway production-only |
| Procedure | Still `docs/milestone-6-gmail-proof.md` (manual owner approve) |
| Unapproved sends | 0 (flag OFF; no connector) |

## Exact flag states (production)

| Flag | State |
|------|-------|
| `RAG_ENABLED` | OFF (default) |
| `SEND_EMAIL_ENABLED` | OFF |
| `CALENDAR_ACTIONS_ENABLED` | OFF |
| `CRM_ACTIONS_ENABLED` | OFF |

No production flags were flipped during this run.

## Redrive / idempotency / cross-tenant / audit

| Concern | Status |
|---------|--------|
| Calendar redrive | not live-run (provider missing) |
| Gmail redrive | not live-run |
| CRM Action Executor redrive | not live-run |
| Cross-tenant CRM (SQL scoped) | pass (0 leak / 0 wrong-tenant update) |
| Cross-tenant Calendar/Gmail | N/A (no provider) |
| Audit `os_tool_executions` live | **not proven** (needs service key + approve path) |

## Rollback

Unset / set `=0` for each flag. Runner records the same rollback map in JSON artifacts.

## Verdict inputs

Live-proof Definition of Done is **not** met: Calendar, CRM Action Executor, and Gmail staging smokes remain blocked on credentials/OAuth; RAG live tenant KB empty; Railway has no staging environment for flag isolation.
