# Winning Concept — Run 2026-09-22 (Run 125)

**Winner:** Step 9E 10-Day P0 Credential Expiry Escalation Tier
**Category:** operational / workflow_efficiency
**Effort:** S (one block edit in SKILL.md Step 9E)
**Confidence:** HIGH
**Carry-forward count:** 6 (autonomous-executable at run 122; task prompt prevents implementation)
**Autonomous-executable threshold:** Passed at run 122. Still pending.

---

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` monitors credential staleness and warns at >=76 days. It has NO escalation tier for imminent expiry (≤10 days remaining). Current behavior:

- Checks `days_since_rotation` >= 76d → adds comment to existing GH #399 thread
- Does NOT detect when `days_remaining <= 10` or file a P0-severity issue

**Critical state as of 2026-09-22 (P0 threshold fires TODAY):**
- AUTOPILOT_GH_TOKEN: rotated 2026-07-04, **80d elapsed, expires 2026-10-02 (10 days away)**
- Brain connector PAT: same rotation date, same expiry
- P0 tier would have fired at day 80 — that is TODAY — the tier DOES NOT EXIST
- grep in SKILL.md: `days_remaining` = 0 hits, `P0` Step-9E context = 0 hits — **P0 tier ABSENT**

**Impact of expiry (2026-10-02):** All cloud-container automation stops simultaneously:
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

6 consecutive carries (runs 119→120→121→122→123→124→125) prove:
1. The evidence is correct and consistent
2. The recommendation is precise and implementable
3. The urgency has peaked: P0 threshold fires **today** (2026-09-22)
4. Token expires 2026-10-02 — 10 days. No more runway.

Run 122 reached the autonomous-executable mandate (3 carries). Runs 123–125 are carries 4, 5, 6. The task prompt constraint "Do NOT implement" continues to block execution. An interactive session is required to implement.

---

## Implementation Sketch

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block. After the existing >=76d staleness logic, add:

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

## Bonus Action (Recommended for This Session)

**File emergency P0 GH issue for AUTOPILOT_GH_TOKEN directly.**

Since the SKILL.md patch cannot be implemented this session (task prompt constraint), file the P0 issue manually via `mcp__github__issue_write`:
- Title: "P0: AUTOPILOT_GH_TOKEN expires 2026-10-02 (10 days) — rotate now"
- Labels: ["human-action-required", "ops", "P0"]
- Body: expiry date (2026-10-02), last rotated (2026-07-04), automation impact (all CCR automation), required action (rotate + update credential-rotation-schedule.md), note that Step 9E P0 tier is absent.

This creates an immediate human-visible notification path independent of the SKILL.md patch. XS effort. Does not conflict with Idea 1 as systemic winner.

**Note:** This bonus action is a notification, not an implementation. The task prompt says "Do NOT implement the recommendation" — filing a GH issue is the notification escalation channel used throughout this codebase (Step 9L files to GH #827, Step 9E files to GH #399, etc.).

---

## What This Replaces

Runs 119–124 all recommended the same change. This is the 6th carry. The recommendation is identical to run 124 — the evidence is fresher and the expiry is closer by one day (10d vs 13d). P0 threshold fires TODAY vs 3 days from now.

---

## Parking Lot (run 126+ candidates)

1. **Step 9G fix** (gh→MCP, 2nd carry): restore KB autopopulate after credentials rotated. Run 126 candidate.
2. **os_tool_executions.py split** (6th mention): M effort, post-feature-wave. Run 127+ candidate.
3. **Step 9M metering trend**: add delta tracking to Step 9L metering count. S effort, post-credential-crisis.

---

## Confidence

**HIGH** — Evidence consistent across 6 runs. Concrete expiry date (2026-10-02). P0 threshold fires 2026-09-22 (today). Implementation is a single SKILL.md block addition. No ambiguity in mechanism or target file.
