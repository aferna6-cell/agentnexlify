# Improvement Backlog — 2026-07-30 (Run 101)

## Active — Proposed This Run

### Step 9H: GH Actions CI Systematic Failure Alerter (WINNER)
**Status:** Recommended — pending human approval
**Category:** operational
**Effort:** XS (~25 bash lines in SKILL.md)
**Evidence:** GH Actions spending limit blocked ALL CI for 11+ days (#500 open). 40+ ai-ready issues stalled. Morning digest DAY 9 #1 priority. Zero automated detection fired during the 11-day blind spot.
**Action:** Add Step 9H bash block to nightly-commit-review SKILL.md. When 0 workflow successes AND ≥3 workflow types failing in last 48h: file `human-action-required + infra` GH issue. Dedupe guard prevents duplicate issues.
**Next run mandate:** Verify Step 9H present in SKILL.md (grep 'Step 9H'). Verify nightly fired it if GH Actions still dark. Verify no duplicate issues filed if spending limit resolved.

---

## Bonus Actions (Autonomous — Executed This Run)

### Bonus A: PR #577 escalation comment (Step 9G urgency)
**Status:** EXECUTED — comment posted on PR #577
**Framing:** KB threshold crossed today (7 days), PR is SKILL.md-only (safe to merge without CI), Step 9G self-heal needed.

### Bonus B: Paying tenant silence monitoring GH issue
**Status:** EXECUTED — GH issue filed with SQL query + monitoring sketch
**Framing:** bug-patterns.md documents 5-week silent outage, Keys Koffee. Issue contains copy-paste SQL for human to wire to monitoring.

---

## Parking Lot

### Step 9G (Carry-Forward from Run 100) — KB Autopopulate Self-Healing Trigger
**Status:** 1st carry-forward cycle. PR #577 DRAFT (8 days). KB threshold crossed today.
**Promote:** If PR #577 not merged by run 102 (2nd carry-forward), escalate to direct implementation (Step 9F pattern: 3-cycle = direct write to SKILL.md at run 103).
**Promote also if:** GH Actions spending limit resolved (CI unblocks) AND human can merge PRs normally.

### Autonomy Loop Daily Health Check
**Status:** WEAKENED — sweeper (#608) is 24h old. Premature to add daily observability.
**Promote when:** 2+ stranded run incidents confirmed, OR autonomy loop has been actively cycling for ≥1 week.
**Notes:** `run_loop list` reads flat files (no network), safe in headless context. Step 9I candidate once evidence justifies.

### Paying Tenant Silence Alerter
**Status:** WEAKENED — Supabase MCP unavailable in headless nightly. GH issue filed as Bonus B.
**Promote when:** Human wires monitoring query to GH Actions or Supabase webhook. Requires `SUPABASE_ACCESS_TOKEN` in GH Actions secrets.

### graph/runtime.py God-Class Pre-Emption
**Status:** WEAKENED — 516 lines (86% of 600 threshold). Not yet above threshold.
**Promote when:** Lines exceed 550 (next check), or when a new PR adds graph execution responsibilities to runtime.py.

### LoopHealthPage.jsx
**Status:** Deferred — promote when Agent OS >5 active tenants (currently 2-3).

---

## Rejected This Run

*(No new rejections — debate produced weakened parking-lot entries, not hard kills.)*

---

## Questions for Next Run
1. Is Step 9H present in SKILL.md? Did nightly fire it since GH Actions went dark on 2026-07-21?
2. Has the GH Actions spending limit been resolved? Is CI green again?
3. Has PR #577 (Step 9G) been merged? What is KB freshness?
4. Has the autonomy loop completed at least 1 full cycle (issue → PR → merge) since PR #599 shipped?
5. Is graph/runtime.py above 550 lines? (Check after next round of autonomy development.)
