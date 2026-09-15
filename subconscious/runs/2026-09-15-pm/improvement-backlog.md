# Improvement Backlog — Updated Run 121 (2026-09-15-pm)

## Active (in escalation queue)

### Step 9E: Credential Expiry Escalation — Earlier Warning + GH Issue Filing
- **Status:** 3rd carry-forward → autonomous-executable at run 122
- **Evidence:** AUTOPILOT_GH_TOKEN 73d (fires at 76d), expires 2026-10-02. 10-day early warning window missed 7 days running.
- **Implementation:** Add `days_remaining <= 10` threshold to Step 9E with GH issue dedup guard
- **File:** `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block
- **Owner:** Human (recommended) OR autonomous at run 122

---

## Parking Lot (verified, not urgent enough to win)

### os_tool_executions.py God Class Split
- **Status:** Recurring candidate since run 116. Modified 2026-09-11 (4 days ago) — defer until stable.
- **Evidence:** 783 lines. CLAUDE.md Rule 9 threshold = 600L. File on critical tool execution path.
- **Next check:** Run 122 — if no modifications in 7+ days, elevate to candidate.
- **Effort:** M (3-5 hours, multi-file refactor)

### AI Metering Violations → ai-ready Issues
- **Status:** GH #871 filed (44 violations). Step 9D at 0 ai-ready issues. Loop status unverified.
- **Evidence:** check_ai_metering.py rc=2, 20 router violations + 24 service violations.
- **Prerequisite:** Verify issue-to-pr loop operational before filing sub-issues (GH #500 dark Actions context).
- **Next check:** Run 122 — verify loop, then file 3-5 scoped ai-ready issues.
- **Effort:** S (1-2 hours to scope and file)

### Step 9G: KB Autopopulate Self-Heal via MCP
- **Status:** WEAKENED. gh CLI unavailable in cloud sessions. Proposed fix uses mcp__github__actions_run_trigger.
- **Prerequisite:** Verify `workflow_dispatch` in `.github/workflows/kb-autopopulate.yml`. Verify MCP tool available in nightly sessions.
- **Next check:** Run 122 — verify prerequisites, then evaluate.
- **Effort:** S (1 hour to verify + implement)

---

## Killed This Run

### Step 9J Major Version PR Escalation
- **Killed:** Dependabot PRs are already the tracking mechanism. Filing GH issues would be duplicate tracking.
- **Date killed:** Run 121 (2026-09-15-pm)

---

## Frozen (rejected 3+ times)

### ai_human_handoff
- **Frozen since:** Governance.json `frozen_ideas` list. Do not propose.

---

## Recently Implemented (reference)

### Step 9L: AI Usage Guard Coverage Sweep
- **Implemented:** `.claude/skills/nightly-commit-review/SKILL.md` lines 457/471
- **Verified:** Today's nightly ran check_ai_metering.py, filed GH #871 (44 violations)
- **Date:** Confirmed operational as of 2026-09-15

### Step 9I: Demo Role Security Sweep
- **Implemented:** Nightly Step 9I
- **Verified:** Today's nightly filed GH #870 (90+ files missing block_demo_role)
- **Status:** Operational

### Step 9J: Dependabot Auto-Merge
- **Implemented:** Nightly Step 9J
- **Verified:** Merged #868 today. Correctly skipped 4 major version bumps + 1 CI-unstable.
- **Status:** Operational

### Step 9K: Stale Subconscious PRs
- **Implemented:** Nightly Step 9K
- **Verified:** Today's nightly reported 0 open subconscious PRs — PASS.
- **Status:** Operational
