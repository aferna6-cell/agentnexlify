# Candidate Ideas — Run 121 (2026-09-16-pm)

Evidence window: 2026-09-13 → 2026-09-16 | 1 commit reviewed (clean, docs only)

---

## Idea 1: Step 9E Credential Expiry Escalation — 2nd Carry-Forward (WINNER)

**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit in SKILL.md)
**Carry-forward count:** 2 (was 1st carry-forward in run 120)

**Evidence:**
- AUTOPILOT_GH_TOKEN: 74 days since rotation (threshold 76d, interval 90d). Fires in 2 days. Expires 2026-10-02 (16 days away).
- grep `days_remaining|<= 10` in nightly-commit-review/SKILL.md → 0 matches. Step 9E NOT implemented despite 2 recommendation runs.
- nightly-2026-09-16 confirms: "Step 9E: 2 credentials checked, 0 approaching expiry, 1 unknown state. No open credential-rotation issues found." — 74d is under 76d threshold, so no current trigger. But in 2 days it crosses threshold, and no GH issue will fire.
- 3 consecutive nightly logs (Sep 11 × 2, Sep 16) reported AUTOPILOT_GH_TOKEN approaching threshold with zero human action because Step 9E only logs, never files a GH issue.
- Morning digest 2026-09-16: "Rotate AUTOPILOT_GH_TOKEN today — 16 days left, loop dies if missed."
- PR #874 (DRAFT, 1 day old) exists with implementation sketch.
- Escalation precedent: Steps 9F/9G/9I/9J/9K all auto-implemented on 3rd carry-forward.

**Autonomous-executable at run 122** (3rd carry-forward).

---

## Idea 2: Step 9G MCP Trigger Fix

**Category:** operational
**Effort:** S (2-line edit in SKILL.md + verification)
**Carry-forward count:** 0 (new idea, previously "parked" in run 120)

**Evidence:**
- nightly-2026-09-16 Step 9G: "gh CLI not available in this environment. Cannot trigger workflow run."
- KB autopopulate last run: 2026-08-26 (21 days stale, threshold 7 days).
- Brain connector last run: 2026-07-23 (55 days stale, threshold 14 days).
- Both staleness issues trace to the same root cause: Step 9G cannot trigger the GH Actions workflow because `gh` CLI is unavailable in cloud sessions.
- Fix: replace `gh workflow run kb-autopopulate.yml` with `mcp__github__actions_run_trigger` call.
- Caveat: needs verification that (a) `kb-autopopulate.yml` has `workflow_dispatch` trigger, (b) `mcp__github__actions_run_trigger` is available and authorized in nightly sessions.

**Risk:** If the `actions_run_trigger` MCP tool isn't available in the nightly execution context, fix creates a silent failure mode instead of an obvious one. Pre-verification required before implementation.

---

## Idea 3: AI Metering Hotpath Triage — GH #875 Pickup

**Category:** code_health
**Effort:** M (40 violations across 16 routers + 24 services, needs systematic review)
**Carry-forward count:** 0 (GH #875 filed 2026-09-16, fresh issue)

**Evidence:**
- check_ai_metering.py: 40 violations (16 routers, 24 services). Count dropped from 44 to 40 after #871 (4 fixes landed).
- GH #875 filed by nightly-2026-09-16. Labels: ai-ready, nightly-review, billing.
- Morning digest: "Real cost risk: any tenant on free plan can burn unbounded tokens via these paths."
- ai-ready label = issue-to-pr-loop eligible. But morning digest says "needs a human to confirm scope first."
- Issue is 0 days old — subconscious recommending action this run would duplicate what the morning digest already surfaced as priority #2.

**Objection:** Issue is already filed and labeled ai-ready. Subconscious adding a recommendation this run is redundant — the issue-to-pr-loop should pick this up. Better to let that automation run its course than to carry forward as a subconscious recommendation.

---

## Idea 4: React 19 Upgrade Gate in Step 9J

**Category:** workflow_efficiency
**Effort:** XS (comment/doc update in SKILL.md, no code change needed)
**Carry-forward count:** 0

**Evidence:**
- 5 open Dependabot PRs: #863 react-dom 18→19, #861 react 18→19 (demo-platform), #860 react 18→19 (frontend), #859 vitest 4→5, #864 mcp >=2.2.0,<3.
- Step 9J currently skips all because they're major version bumps.
- Morning digest: "React 19 PRs #860 and #863: do NOT merge without running frontend build + E2E smoke."
- Stagnant queue: if Step 9J never merges these, Dependabot will keep sending reminders and the queue grows.
- Proposed fix: Step 9J should comment on the React 19 PRs once with human-action-required tag rather than silently skipping every nightly.

**Objection:** Low value compared to credential expiry. The PRs are already visible in morning digest. Adding a Step 9J comment mechanism is more work (S+ effort) than the value it delivers right now.

---

## Idea 5: os_tool_executions.py God Class Split

**Category:** code_health
**Effort:** L (783L file, complex dependencies)
**Carry-forward count:** 4+ (noted in runs 116-120 as candidate)

**Evidence:**
- 783 lines. God class pattern.
- Was stable for 7 days before run 116 flagged it. Then run 120 noted: modified 2026-09-11 (stability window broken).
- No evidence of active bugs. No test failures linked to this file.
- Complexity risk: splitting a recently-modified file without understanding what changed on Sep 11 is risky.

**Objection:** Low urgency vs credential expiry. Stability window broken (modified 2026-09-11 = 5 days ago). No active bug. The right move is to wait until the file stabilizes (14+ days unchanged) before recommending a split.

---

## Ranking

| Rank | Idea | Urgency | Effort | Confidence |
|------|------|---------|--------|------------|
| 1 | Step 9E 2nd carry-forward | CRITICAL (16d to expiry) | XS | HIGH |
| 2 | Step 9G MCP fix | HIGH (KB 21d stale) | S | MEDIUM (needs pre-verify) |
| 3 | AI metering triage | HIGH (cost risk) | M | HIGH (but already filed/labeled) |
| 4 | React 19 gate in 9J | LOW | XS | MEDIUM |
| 5 | os_tool_executions.py split | LOW | L | LOW (stability broken) |
