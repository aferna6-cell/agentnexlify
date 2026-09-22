# Run 126 — Improvement Backlog

Ranked by priority. Winner excluded (see winning-concept.md).

---

## 1. Step 9E: P0 Credential Expiry Tier [PARKING LOT]
- **What:** Add `days_remaining <= 10` escalation block to SKILL.md Step 9E
- **Why parked:** GH #893 handles immediate P0. Task-prompt constraint blocks implementation after 6 carries.
- **Status:** autonomous-executable since run 122 — execute when constraint lifted
- **Urgency:** AUTOPILOT_GH_TOKEN expires 2026-10-02. Human action window: 10 days.

## 2. GH #892: CI Safety Test Escape [CONSULT NEXT SESSION]
- **What:** Staging credential rejection test escaping to network. P1 blocker.
- **Why deferred:** Outside subconscious scope (code bug, not workflow automation). No subconscious commit should touch test files unilaterally.
- **Action:** Route to nightly-commit-review auto-fix (LOW risk if mock boundary fix) or compound-engineering session

## 3. Dependabot PR Queue [MONITOR]
- **What:** 6 new PRs (#885–#891): bcrypt, supabase, uvicorn, google-api-python-client, vitest, jsdom
- **Why deferred:** Step 9J handles these but has skip throughput issue. Monitoring.
- **Immediate action available:** Human can merge all 6 manually — morning digest labels them "safe maintenance bumps"
- **Step 9J audit:** Audit skip threshold and `max_prs_per_run` limit in future run

## 4. os_tool_executions.py God-Class [SPEC NEEDED]
- **What:** 783 lines, GH #881 open, 6th consecutive appearance in evidence
- **Why deferred:** No spec exists. Refactor without spec violates user-rules Rule 1.
- **Next action:** Write split spec as GH #881 comment (S effort, high compounding value)

## 5. Step 9J Dependabot Throughput [FUTURE RUN]
- **What:** 17/19 PRs skipped per run. Token budget or risk-scoring threshold too conservative.
- **Why deferred:** Not urgent. Queue manageable manually. Audit in future run.

---

## Mandate Carry-Forwards

The following governance mandates remain open:

| Item | Status | Age |
|------|--------|-----|
| Step 9E P0 tier in SKILL.md | ABSENT — waiting on constraint lift | 6 runs (119→126) |
| AUTOPILOT_GH_TOKEN rotated | NOT ROTATED — GH #893 open | 80d since rotation |
| Brain PAT rotated | NOT ROTATED | 80d since rotation |
| ops/credential-rotation-schedule.md updated | STALE | — |
| GH #892 CI fix | OPEN 1d | — |
