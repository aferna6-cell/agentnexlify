# Winning Concept — Run 2026-09-18-pm (Run 123)

**Winner:** Step 9E 10-Day P0 Credential Expiry Escalation Tier
**Category:** operational / workflow_efficiency
**Effort:** S (one block edit in SKILL.md Step 9E)
**Confidence:** HIGH
**Carry-forward count:** 4 (was autonomous-executable at run 122, task prompt prevents implementation)
**Autonomous-executable threshold:** Was 3 carries → threshold passed at run 122. Still pending.

---

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` monitors credential staleness and warns at >=76 days (14-day warning before 90-day expiry). It has NO escalation tier for imminent expiry (≤10 days remaining). Current behavior:

- Checks `days_since_rotation` >= 76d → adds comment to existing GH #399 thread
- Does NOT detect when `days_remaining <= 10` or file a P0-severity issue

**Critical state as of 2026-09-18:**
- AUTOPILOT_GH_TOKEN: rotated 2026-07-04, 76d elapsed, **expires 2026-10-02 (14 days away)**
- Brain connector PAT: same rotation date, same expiry
- P0 tier would fire at day 80 — in ~4 days (2026-09-22)

**Impact of expiry:** All cloud-container automation stops simultaneously:
- Nightly commit reviews (no GitHub API access)
- Subconscious loop commits (no git push via token)
- Issue-to-pr-loop (no PR creation)
- KB autopopulate triggers (no workflow dispatch)

**Why existing Step 9E is insufficient:**
- GH #399 has 7+ autonomous comments, 0 human responses — the thread is noise
- A new P0-labeled GH issue (`human-action-required + ops + P0`) generates a fresh email notification and surfaces in P0 views
- P0 urgency tier is categorically different from a staleness comment

---

## Why This, Why Now

4 consecutive carries (runs 119→120→121→122→123) prove:
1. The evidence is correct and consistent
2. The recommendation is precise and implementable
3. The urgency increases with each carry: AUTOPILOT_GH_TOKEN moves from "approaching" to "expiring"
4. The P0 tier would have fired at day 80 (~2026-09-22) — if not implemented before then, the first chance to catch it is gone

The carry-forward pattern is itself evidence that this gap is real and persists. Each run adds 1-2 days of urgency.

---

## Implementation Sketch

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block. After the existing >=76d staleness logic (around line 289-300), add:

```
    5. **P0 escalation for imminent expiry (days_remaining <= 10):**
       For each credential flagged approaching_expiry (from step 3 above):
         Compute days_remaining = next_due_date - today
         (next_due_date = last_rotated_date + interval_days from credential-rotation-schedule.md)
         If days_remaining <= 10:
           a. Search open GH issues with labels: ["P0", "ops"] AND title contains credential name
              — dedup guard: if open P0 issue already exists for this credential, add comment only
           b. If NO open P0 issue found:
              File GH issue via mcp__github__issue_write:
                title: "P0: {credential_name} expires in {days_remaining} days — rotate now"
                labels: ["human-action-required", "ops", "P0"]
                body: |
                  **{credential_name}** expires on {next_due_date} ({days_remaining} days).
                  Last rotated: {last_rotated_date} ({days_since_rotation} days ago).
                  **Automation impact:** {systems_using_credential}.
                  **Action:** Rotate token and update ops/credential-rotation-schedule.md.
              Log: "Step 9E P0: {credential_name} — P0 issue filed (expires {days_remaining}d)"
           c. If open P0 issue found: add comment with updated days_remaining count.
       Update log line: "Step 9E: {N} checked, {M} at threshold, {K} P0 (≤10d), {L} unknown"
```

Note: `next_due_date` can be derived from `ops/credential-rotation-schedule.md` column "Next due" if present, or computed as `last_rotated + interval`.

---

## What This Replaces

Run 122 was the same recommendation. This run continues the carry-forward. No previous winner is displaced — this is a build on the established direction.

---

## Bonus Action (Mandate Item)

File GH issue for os_tool_executions.py god class split (6th consecutive mention, run 123 mandate):
- Title: "refactor(os_tool_executions.py): split 783L god class into focused modules"
- Labels: `tech-debt`, `ai-ready`
- Body: current LOC, 3-4 natural split planes (action persistence, event dispatch, quota tracking, tool registry bridge)

---

## Confidence

**HIGH** — Evidence is consistent across 4 runs. Concrete expiry date (2026-10-02). Implementation is a single SKILL.md block addition. No ambiguity in mechanism or target file.
