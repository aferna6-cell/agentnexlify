# Nightly Commit Review — 2026-07-21

**Run time:** 2026-07-21 UTC  
**Window:** last 24 hours  
**Commits reviewed:** 45  
**Auto-fixes applied:** 0  
**Issues filed:** 0 (infrastructure action documented below)  
**Critical invariant violations:** NONE

---

## Triage Summary

### HIGH — Informational (reviewed, no code defects found)

| SHA | Description | Verdict |
|-----|-------------|---------|
| `37ba729` | feat(photo-quote): metered billing 500/mo cap + $0.15 overage | CLEAN — correct `client_id` column, daily quota (50/day) + monthly cap (500/mo) are separate layers. Both fail-open. |
| `dd23ba9` | feat(ops-automation): signed-JWT auth core for widget booking | CLEAN — HS256, 5-min TTL, jti replay guard, injectable `now` for deterministic tests. No `tenant_id` on leads/conversations tables. |
| `4a61a4a` | feat(ops-automation): widget booking router — dual auth + 409 alternates | CLEAN — `appointments` table correctly uses `tenant_id` (schema-discipline: `client_id` rule is leads/conversations only). |
| `ec0de08` | security(#266): vault-route last integrations readers + prep plaintext sunset | **ACTION REQUIRED** (see below) |

### MEDIUM — Informational

| SHA | Description | Notes |
|-----|-------------|-------|
| `18ad432` | feat(photo-quote): Quote Requests dashboard tab + usage meter | New admin endpoints + React page. `client_id`-scoped correctly. Router passes URL `tenant_id` to service `client_id` param — expected pattern. |
| `e0aa720` | feat(photo-quote): widget photo-quote endpoint | `client_id`-scoped. Daily + monthly rate limits layered. |
| `3cb3392` | feat(ops-automation): missed-call text-back plan gate | Uses `pending_automations` table (migration 180). Code fails gracefully if table absent. |
| `9573d48` | feat(photo-quote): 30-day full-image retention purge cron | Cleanup job — fail-safe (logs, doesn't raise). |
| `34fa9bd` | feat(ops-automation): booking↔GCal core write-back | `tenant_id`-scoped (`appointments` table — correct). |
| `44f9042` | feat(widget): conversation memory tier | Migration 182 DRAFT/UNAPPLIED — pending peer apply via Supabase MCP. `chat_messages` table uses `tenant_id` (correct). |
| `e20356a` | feat(kb): article provenance | Migration 181 DRAFT/UNAPPLIED — pending peer apply. |
| `b17ed5c` | feat: enterprise-audit adopt-cheaply items (7) | New MCP, OS routers, activity export — all correctly tenant-scoped. Migrations 177-179 included. |
| `599d90d` | Split widget_chat.py god class | Major refactor — fully tested (976-test pipeline suite). |
| `2816310` | Split invoices.py god class | Major refactor — 1006-test router suite. ADR added. |
| `ba10d80` | feat: autonomous cross-provider team protocol | Structural — no production code changed. |

### LOW — No action needed

Dependency bumps (14 commits), docs/KB updates (7 commits), subconscious/tooling (3 commits), routine logs (2 commits).

---

## Action Required

### 🔒 Migration 176 — INTEGRATIONS_ENC_KEY must be provisioned first

**Commit:** `ec0de08`  
**File:** `migrations/176_sunset_plaintext_integration_tokens.sql`  
**Risk:** HIGH (irreversible schema change — drops `access_token` + `refresh_token` from `integrations` table)

The migration file explicitly documents:
> "DO NOT APPLY until INTEGRATIONS_ENC_KEY is set in Railway prod (and CI). Without the key the vault's encrypt_oauth_tokens() no-ops, so new OAuth connects would have nowhere to store tokens after this drop."

**Current state:** Migration is committed but NOT applied (status marked clearly in file). Prod `integrations` table has 0 rows (verified by PR author). All readers now route through `decrypt_integration_row` (confirmed in ec0de08).

**Next step:** Human must provision `INTEGRATIONS_ENC_KEY` in Railway prod, then apply via `mcp__supabase__apply_migration` or SQL editor.

---

## Unapplied Migrations (By Design — Pending Peer Apply)

| Migration | Status | Blocker |
|-----------|--------|---------|
| 180 (`pending_automations`) | Noted as potentially unapplied | Missed-call text-back will silently no-op until applied |
| 181 (`kb_article_provenance`) | DRAFT — peer review | Team contract: fable5 authored; peer must apply |
| 182 (`conversation_message_memory`) | DRAFT — peer review | Same |

---

## CLAUDE.md Critical Invariants — All Clear

| Rule | Status |
|------|--------|
| `client_id` not `tenant_id` on leads/conversations | ✅ All new code correct |
| `status` not `lead_stage` | ✅ Not touched |
| `areas_of_interest` not `service_interest` | ✅ Not touched |
| No `from __future__ import annotations` in FastAPI files | ✅ None in today's commits |
| Widget JS byte-identical (3 locations) | ✅ No widget JS changes today |
| No secrets in commits | ✅ |
| Schema changes via numbered migrations | ✅ (176-182 all numbered) |

### Pre-existing low-risk finding (not from today)
`backend/tests/test_local_seo_handlers.py:8` has `from __future__ import annotations`. Last modified 2026-07-18 (not in today's window). Test files don't affect Pydantic resolution at runtime. Low risk, pre-existing.

---

## Auto-Fixes Applied

None. No LOW-risk bugs identified in today's commits that warranted auto-fix.

---

## Stats

- Total commits: 45
- Deps/chore: 16
- Docs/KB: 8
- New features: 14
- Refactors: 4
- Ops/tooling: 3
- HIGH triage: 4 (3 clean, 1 needs human action)
- MEDIUM triage: 11
- LOW triage: 30
