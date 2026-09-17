# Improvement Backlog — Run 2026-09-17-pm (Run 121)

## Active (this run's winner)

### Fix Step 9G: Replace `gh workflow run` with `mcp__github__actions_run_trigger`
- **Category:** workflow_efficiency / operational
- **Effort:** XS
- **Status:** Recommended — awaiting human approval OR run 124 autonomous-executable
- **Implementation:** Edit Step 9G block in `.claude/skills/nightly-commit-review/SKILL.md`
  - Replace `gh workflow run kb-autopopulate.yml --repo aferna6-cell/agentnexlify` with `mcp__github__actions_run_trigger` call
  - Handle success: log trigger
  - Handle failure: comment on GH #403 with diagnostic

---

## Parking Lot (carry-forward items)

### Step 9E: 10-Day Early Warning for Credential Rotation (3rd carry-forward → autonomous-executable at run 122)
- **Effort:** XS
- **Status:** AUTOPILOT_GH_TOKEN at 76d+ (threshold crossed). Existing ≥76d logic fires now.
  10-day early warning still absent. Per run 120 escalation path: run 122 = autonomous-executable.
- **Next:** run 122 should implement directly (3rd carry-forward per precedent Steps 9F/9G/9I/9J/9K/9L)
- **Note:** Even though existing logic fires at 76d, the 10-day early warning catches rotations BEFORE they enter the threshold window. Value deferred to next rotation cycle (December 2026).

### Split os_tool_executions.py God Class (783L)
- **Effort:** M
- **Status:** 4th consecutive run noting this file. Requires human approval (M effort, not autonomous-executable).
- **ESCALATION NOTE:** 4 consecutive subconscious runs without action. This is a human-action item.
  Owner should schedule this split before run 125 (5th mention would indicate systemic neglect).
- **Suggested split:** `tool_dispatching.py`, `tool_validation.py`, `tool_result_processing.py`, `os_tool_executions.py` (thin coordinator)
- **Risk:** Medium. All import call sites must be updated. No schema changes.

---

## Rejected / Killed (this run)

### Step 9L Closed-Issue Dedup Guard
- **Status:** Parking lot — one cycle only; insufficient evidence for recurring pattern
- **Condition to re-evaluate:** Second consecutive nightly where owner closes a filed GH issue as "duplicate"

### Dependabot Major-Version Consolidated Tracking Issue
- **Status:** Low leverage; owner likely has mental queue
- **Condition to re-evaluate:** When Dependabot PRs age 30+ days without any comment

---

## Standing Human-Action Required

| Item | GH Issue | Age | Status |
|------|----------|-----|--------|
| AUTOPILOT_GH_TOKEN rotation | GH #399 | 75d overdue | Step 9E fires today (76d threshold) |
| Brain connector SUPABASE_ACCESS_TOKEN | GH #800 | 56d stale | human-action-required |
| KB autopopulate ANTHROPIC_API_KEY | GH #403 | 22d stale | human-action-required |
| AUTOPILOT_GH_TOKEN: add to Railway | GH #399 | — | Expires 2026-10-02 (15 days) |
