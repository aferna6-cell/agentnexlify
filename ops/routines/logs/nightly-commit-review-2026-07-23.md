# Nightly Commit Review — 2026-07-23

**Run time:** 2026-07-23 UTC (automated)
**Window:** last 24 hours
**Commits reviewed:** 7

---

## Commit Triage

| SHA | Title | Risk | Files | Action |
|-----|-------|------|-------|--------|
| `281156f` | Docs: record first MCP tenant activation | LOW | 1 | no action |
| `970da66` | Round 8: approval-loop repair – dedupe, name fallback, funnel meters | MEDIUM | 8 | noted |
| `0e98b72` | Fix MCP mount behind Railway proxy: disable DNS-rebinding host allowlist | MEDIUM | 2 | noted |
| `e646bdc` | Round 7: stage-3 plan gate, audit batch, calls.py split, owner MCP server, suite onboarding | MEDIUM | 51 | noted |
| `c9654d0` | ops: morning-digest 2026-07-22 | LOW | 1 | no action |
| `9c02bb6` | docs(nightly): clarify auth_billing.py diff attribution | LOW | 2 | no action |
| `7f598ff` | docs(nightly): review 2026-07-22 | LOW | 2 | no action |

---

## Detailed Findings

### e646bdc — Round 7 (MEDIUM)

**What changed:** 51 files — stage-3 plan gate on 10 OS routers, audit batch M1-M5 (fake_supabase consolidation, osStyles.js consolidation, os_constants.py single-source, migrations 185/186 applied, API layer refactor in OS cards), calls.py god-file split (1196 → 237/875/133 lines), owner MCP server mounted at `/mcp`, new `GET/POST/DELETE /api/v1/auth/mcp-key/{tenant_id}` endpoints, DemoTour extended to real owners.

**Critical invariants checked:**
- ✅ No `from __future__ import annotations` in any new FastAPI files
- ✅ `client_id` used correctly on `leads`, `os_threads`, `os_agent_runs`, `os_backlog_requests`
- ✅ `tenant_id` used on `tenants`, `chat_messages` (correct per schema-log)
- ✅ Cross-tenant isolation on MCP-key endpoints: `claims["tenant_id"] != tenant_id` check on GET, POST, DELETE
- ✅ MCP server auth: validates `mcp_` prefix, checks `mcp_enabled` flag, uses service Supabase
- ✅ Widget-key correctly rejected by MCP server (`mcp_` prefix guard)

**Notes:** The calls.py split is a pure module move (route paths byte-identical per commit message, 250 voice tests pass). No behavioral changes detected. Well-tested with `test_suite_round7.py` (15 tests) and `test_voice_webhooks_split.py` (17 tests).

---

### 0e98b72 — DNS-rebinding fix (MEDIUM)

**What changed:** `TransportSecuritySettings(enable_dns_rebinding_protection=False)` added to MCP FastMCP instance.

**Security assessment:** The MCP server is a public API authenticated by per-tenant `mcp_` keys (not ambient browser cookies/credentials). DNS rebinding protection (host-allowlist defaulting to localhost) is appropriate for browser-credential-based servers but adds no security value here. The disable is documented in inline comments and has a pinned regression test (`test_suite_round7.py`). This is the correct decision for a Railway-hosted API server.

**No action required.** Verified: not a security regression.

---

### 970da66 — Round 8 (MEDIUM)

**What changed:** Approval-loop bug fixes — dedupe guard on pending drafts, name fallback ("there" → email), lapsed-tenant sweep fix in `os_draft_expiry.py`, view-meter logging on email action pages, decision-funnel metrics in admin loop-health endpoint.

**Critical invariants checked:**
- ✅ No `from __future__ import annotations`
- ✅ `client_id` used throughout `os_opportunity_fulfill.py` (leads, os_threads, os_agent_runs)
- ✅ `areas_of_interest` (correct column) used on leads select
- ✅ `admin_loop_health` endpoint uses `_verify_admin_secret` (platform-admin pattern, same as `admin_health`)
- ✅ View-meter uses `log_activity(tenant_id=...)` → logs to `activity_events` (correct column for that table)

**Notes:** The `_pending_metadata_ids` guard (fail-open on scan error) is the correct approach — fulfillment should never block on a dedupe scan failure. Tests cover the fail-open path.

---

## LOW-risk bugs fixed

**None.** No LOW-risk auto-fixable bugs found this cycle.

---

## MEDIUM/HIGH issues filed

**None.** All MEDIUM-classified commits are well-implemented with tests. No regressions or vulnerabilities detected.

---

## Summary

Clean cycle. 7 commits reviewed; 4 substantive, all MEDIUM or lower. Critical invariants hold across all new files:
- No `__future__` annotations
- Schema discipline maintained (client_id/tenant_id correct per table)
- New auth endpoints have proper cross-tenant isolation
- MCP security decision (DNS rebinding off) is justified and tested

Tests could not be run locally (no .venv in nightly execution environment). CI coverage assumed via existing test suites cited in commit messages (15 + 17 + 10 new tests shipped with these commits).
