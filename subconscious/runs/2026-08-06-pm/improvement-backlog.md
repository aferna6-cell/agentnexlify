# Improvement Backlog — 2026-08-06-pm (Run 101)

## Active — Proposed This Run

### Step 9G: KB autopopulate self-healing trigger (WINNER — DIRECT IMPLEMENTATION)
**Status:** DIRECTLY IMPLEMENTED — escalation condition met (6 PR-channel cycles, run 99 precedent)
**Category:** operational
**Effort:** XS (~30 bash lines in SKILL.md)
**Evidence:** KB 14 days stale. Step 9F fires correctly but doesn't trigger repair. 6 unmerged PRs (#606, #611, #613, #625, #626 + earlier) — 2x the 3-cycle escalation threshold.
**Implementation:** Step 9G block written directly to `.claude/skills/nightly-commit-review/SKILL.md` after line 305, committed to main.
**Next run mandate:** Verify Step 9G present in SKILL.md. Verify nightly fired it. Verify KB freshness improved. If kb-autopopulate still failing, check GH Actions secrets (ANTHROPIC_API_KEY, VOYAGE_API_KEY, SUPABASE_ACCESS_TOKEN).

---

## Parking Lot

### Step 9H: Nightly subconscious PR pile-up alerter (REDESIGN REQUIRED)
**Status:** Parking lot — under-specified
**Category:** operational/workflow
**Effort:** S (~20 bash lines in SKILL.md)
**Evidence:** 15 open PRs as of 2026-08-06. 7 subconscious draft PRs.
**Design gap:** Current proposal (comment on oldest PR when count > 3) would fire every nightly indefinitely — noise without convergence. Needs: idempotent alert (fire only on delta increase) or different channel (GH issue, not PR comment).
**Promote when:** Step 9G direct impl + PR pile resolved, AND a new pile-up forms without human action. Then redesign with idempotency.

### Nexlify Score token-burn guard audit (response_score.py)
**Status:** Parking lot — better handled by nightly Step 5
**Category:** code_health
**Effort:** XS (read file + grep ai_usage_guard routing)
**Evidence:** e0e9be6 (2026-08-06) ships `response_score.py` (151 lines, Claude-calling). Nightly reviewed at MEDIUM risk but did NOT verify ai_usage_guard routing. widget_guard.py precedent (run 94) shows this class matters.
**Action:** Add to nightly Step 5 (security/cost review) criteria: "Verify new Claude-calling services route through ai_usage_guard."
**Promote when:** Next nightly commit review fires OR response_score.py receives >1 tenant call-site.

### Typed KB notes discovery prompt for existing tenants
**Status:** Parking lot — customer_value, no technical blocker
**Category:** customer_value
**Effort:** S (~30 lines in KnowledgeSourcesPage.jsx + backend dismiss flag)
**Evidence:** 4853c31 (2026-08-04, PR #632) ships typed KB notes. 3 existing tenants won't discover without in-app notification. No one-time banner pattern exists in dashboard.
**Action:** Dismissible info banner at top of `KnowledgeSourcesPage.jsx`. Dismiss state stored as per-tenant backend flag (CLAUDE.md Rule 6: no localStorage).
**Promote when:** Human merges PR #632 to main AND this surfaces in morning digest as top gap.

### Grandfathered plan gate audit
**Status:** Parking lot — code_health
**Category:** code_health
**Effort:** S (grep + file GH issues)
**Evidence:** 2869124 fixes AI Workforce gate missing grandfathered plan check. Class-of-bug: other gates may have same pattern.
**Action:** `grep -rn 'plan.*==.*"agent_os"\|plan.*in.*\["agent_os"\]' backend/` — find all gates checking agent_os without grandfathered plans.
**Promote when:** Morning digest or next subconscious run elevates this. Or when a grandfathered customer reports feature access issue.

---

## Previously Active (carried forward)

### Step 9F: KB staleness alert → GH #403
**Status:** IMPLEMENTED (run 99 winner, nightly-2026-07-22 confirmed firing)
**Channel:** nightly-commit-review SKILL.md bash block
**Notes:** Working as designed. Step 9G (this run's winner) escalates it.

### Step 9G: KB autopopulate self-healing trigger
**Status:** IMPLEMENTED (run 101 winner, direct escalation to main)
**Channel:** nightly-commit-review SKILL.md bash block
**Notes:** Directly written to SKILL.md in this run (escalation after 6 PR-channel cycles).

---

## Parking Lot (from prior runs)

### LoopHealthPage.jsx — admin frontend for Agent OS loop health
**Status:** Deferred — promote when Agent OS >5 active tenants
**Promote when:** Agent OS tenant count >5 (currently 2-3) OR loop health incident requiring ad-hoc JSON polling

### Voice test regression audit
**Status:** Deferred — nightly reports test pass counts
**Promote when:** Voice test regression detected OR calls.py split adds new files

### Owner MCP "Getting Started" quickstart
**Status:** Deferred — human-authored content, not autonomous
**Promote when:** Second MCP tenant activates OR first tenant reports onboarding friction (currently 1 MCP tenant)

---

## Rejected

### MCP adoption monitoring — Step 9H nightly tracking (prior version)
**Status:** KILLED (run 100 debate)
**Reason:** 1 MCP tenant only. Can't auth-test MCP without tenant key. Pre-emptive observability at 1 tenant wastes nightly real estate.
**Revisit:** 5+ MCP tenants OR MCP outage reported

### ai_human_handoff (FROZEN — 3+ rejections)
**Status:** FROZEN — do not re-propose
