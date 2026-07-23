# Improvement Backlog — 2026-07-23 (Run 100)

## Active — Proposed This Run

### Step 9G: KB autopopulate self-healing trigger (WINNER)
**Status:** Recommended — pending human approval
**Category:** operational
**Effort:** XS (~30 bash lines in SKILL.md)
**Evidence:** KB 10 days stale. Step 9F fired on nightly-2026-07-22 but alert did not trigger repair. kb-autopopulate.yml supports workflow_dispatch.
**Action:** Add Step 9G bash block to nightly-commit-review SKILL.md. When staleness >7 days: trigger gh workflow run, check status after 30s, comment on #403 with specific failure diagnostic if run failed.
**Next run mandate:** Verify Step 9G present in SKILL.md (≥1 occurrence). Verify nightly fired it. Verify KB freshness.

---

## Parking Lot

### LoopHealthPage.jsx — admin frontend for Agent OS loop health
**Status:** Deferred — promote when Agent OS >5 active tenants
**Category:** customer_value / workflow
**Effort:** M (BotHealthPage.jsx as template: 1 JSX file ~120 lines, 1 sidebar entry, 1 route)
**Evidence:** admin_loop_health endpoint operational (22710b3, PR #475). Round 8 adds funnel metrics. Only 2-3 Agent OS tenants active as of 2026-07-23.
**Promote when:** Agent OS tenant count >5 OR a loop health incident occurs requiring ad-hoc JSON polling
**Notes:** BotHealthPage.jsx is the reference template. Admin-secret pattern. Shows: approval-loop status, pending drafts, funnel stage breakdown, decision counts by stage, last-run timestamp.

### Voice test regression audit — verify 250 voice tests green post-Round 7
**Status:** Deferred — nightly already reports test pass counts
**Category:** code_health
**Effort:** S (one pytest run)
**Evidence:** Round 7 (e646bdc) split calls.py (1196→237/875/133). Nightly-2026-07-23 notes "250 voice tests pass" but did not independently verify.
**Promote when:** A voice test regression is detected OR calls.py split adds new files
**Notes:** Lower priority because nightly-2026-07-23 already reports clean.

### Owner MCP "Getting Started" quickstart for tenant onboarding
**Status:** Deferred — human-authored content, not autonomous
**Category:** customer_value / workflow
**Effort:** M (documentation only)
**Evidence:** First MCP tenant activated (281156f). No tenant-facing onboarding guide exists. `docs/dev-knowledge/mcp-owner-server.md` is developer docs only.
**Promote when:** Second MCP tenant activates OR first tenant reports onboarding friction
**Notes:** `MCPSetupPage.jsx` extended in Round 7. Gap between developer docs and tenant quickstart is real. Requires human-authored examples and tenant-voice writing — not autonomous.

---

## Rejected

### MCP adoption monitoring — Step 9H nightly tracking
**Status:** KILLED — evidence too thin, mechanism inadequate
**Category:** operational
**Killed:** Run 100 debate
**Reason:** Only 1 MCP tenant activated as of 2026-07-23. Can't auth-test MCP endpoint without a tenant `mcp_` key (nightly runner doesn't and shouldn't hold tenant credentials). A general health check on `/health` doesn't test MCP-specific functionality. Pre-emptive observability at 1 tenant wastes nightly real estate.
**Revisit conditions:** 5+ MCP tenants activated OR MCP outage reported by a tenant

---

## Previously Active (carried forward from prior runs)

### Step 9F: KB staleness alert → GH #403
**Status:** IMPLEMENTED (run 99 winner, nightly-2026-07-22 confirmed firing)
**Channel:** nightly-commit-review SKILL.md bash block
**Notes:** Working as designed. Step 9G (this run's winner) escalates it.

### BotHealthPage.jsx
**Status:** IMPLEMENTED (PR #475, run 99 findings)

### appointment_completion.py
**Status:** IMPLEMENTED (PR #475, run 99 findings)

### AttributionPage.jsx
**Status:** IMPLEMENTED (PR #475, run 99 findings)
