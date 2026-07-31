# Improvement Backlog — 2026-07-31 (Run 101)

## Active — Implemented This Run

### Step 9G: KB Autopopulate Self-Healing Trigger (DIRECT IMPLEMENTATION)
**Status:** Implemented — applied to SKILL.md this run (escalation precedent from run 99)
**Category:** operational
**Effort:** XS (35 bash lines in SKILL.md)
**Evidence:** KB 8 days stale. Step 9G absent from SKILL.md (grep=0). PR #577 open 8 days unmerged. 2 morning-digest warnings ignored. 3 paying tenants affected.
**Action taken:** Step 9G bash block added directly to .claude/skills/nightly-commit-review/SKILL.md. When staleness >7 days: trigger `gh workflow run kb-autopopulate.yml`, check status after 30s, comment on GH #403 with specific failure diagnostic (names missing secrets) if run fails.
**Next run mandate:** (1) Verify Step 9G present in SKILL.md (≥1 occurrence). (2) Check nightly log for 'Step 9G:' entry. (3) Verify KB freshness improved (knowledge-base/log.md last entry date post-2026-07-23). (4) If kb-autopopulate still failing: check GH #403 for Step 9G diagnostic comment.

---

## Parking Lot — From This Run

### Nightly Autonomy Sweeper Invocation (Step 9I candidate)
**Status:** Parking lot — valid structural gap, lower priority than Step 9G
**Category:** operational
**Effort:** XS (~15 bash lines in SKILL.md)
**Evidence:** `scripts/autonomy/sweeper.py` shipped 2026-07-28 (PR #608, 251 tests). `run_loop sweep` and `run_loop list` CLIs available. No automated sweep runs between Routine firings. A crash mid-verify (exact pattern that caused #605) can strand a run in RUNNING state until manual sweep. Bug-patterns.md doesn't yet list this class; sweeper arrived 3 days ago.
**Action when promoted:** Add Step 9I bash block to nightly SKILL.md: `python3 -m scripts.autonomy.run_loop sweep --dry-run`. If stranded runs found: run live sweep and log count resolved.
**Promote when:** (a) Another stranded autonomy run detected, or (b) Step 9G confirmed firing correctly and KB fresh (capacity available), or (c) Day 7+ from shipping without sweep automation.
**Precondition:** Verify `python3 -m scripts.autonomy.run_loop --help` works in nightly context before wiring.

### INTEGRATIONS_ENC_KEY Escalation (Step 9I candidate)
**Status:** Parking lot — valid escalation pressure, lower priority than autonomy sweeper
**Category:** operational
**Effort:** XS (~20 bash lines in SKILL.md)
**Evidence:** GH #536 open Day 10 (2026-07-31) — INTEGRATIONS_ENC_KEY not provisioned in Railway. Migration 176 blocked. Listed HIGH risk in every nightly review table. No comment escalation has been applied (only table entries in logs, which don't push notifications).
**Action when promoted:** When GH #536 OPEN AND age >7 days → post escalation comment (max once per week — check for existing escalation comment before posting). Frame: "Day N: migration 176 cannot be applied until INTEGRATIONS_ENC_KEY is provisioned in Railway Variables → Deploy."
**Debate verdict:** WEAKENED — pure pressure escalation with no new information value. Effective but lower than autonomy sweeper on urgency (migration 176 affects a dormant feature, not live paying tenants).
**Promote when:** (a) Autonomy sweeper Step 9I implemented, or (b) GH #536 crosses Day 21+.

---

## Parking Lot — Carried From Run 100

### LoopHealthPage.jsx — admin frontend for Agent OS loop health
**Status:** Deferred — promote when Agent OS >5 active tenants
**Category:** customer_value / workflow
**Effort:** M (~120 lines JSX + sidebar entry + route; BotHealthPage.jsx as template)
**Promote when:** Agent OS tenant count >5 OR loop health incident requiring ad-hoc JSON polling

### Voice test regression audit — verify 250 voice tests green post-Round 7
**Status:** Deferred — nightly already reports test pass counts
**Category:** code_health
**Effort:** S (one pytest run)
**Promote when:** Voice test regression detected OR calls.py split adds new files

### Owner MCP "Getting Started" quickstart for tenant onboarding
**Status:** Deferred — human-authored content, not autonomous
**Category:** customer_value / workflow
**Effort:** M (documentation only)
**Promote when:** Second MCP tenant activates OR first tenant reports onboarding friction

---

## Rejected

### MCP adoption monitoring — Step 9H nightly tracking (carried from run 100)
**Status:** KILLED
**Date:** 2026-07-23
**Reason:** Only 1 MCP tenant activated. Cannot auth-test MCP endpoint without tenant `mcp_` key (security anti-pattern). General `/health` check doesn't test MCP-specific functionality. Pre-emptive observability wastes nightly SKILL.md real estate.
**Revisit when:** 5+ MCP tenants activated OR MCP outage reported by a tenant.

---

## Previously Active — Resolved

### Step 9F: KB staleness alert → GH #403
**Status:** IMPLEMENTED (run 99 winner, nightly-2026-07-22 confirmed firing — "Step 9F: KB STALE (9 days) — comment added to GH #403")

### Step 9G: KB autopopulate self-healing trigger
**Status:** IMPLEMENTED (run 101 direct implementation, escalation precedent, 2026-07-31)
