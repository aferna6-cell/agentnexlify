# Winning Concept — Run 2026-09-20 (Run 126)

**Winner:** Step 9E 10-Day P0 Credential Expiry Escalation Tier
**Category:** operational / workflow_efficiency
**Effort:** S (one block edit in SKILL.md Step 9E)
**Confidence:** HIGH
**Carry-forward count:** 7 (autonomous-executable at run 122; task prompt prevents implementation)
**Autonomous-executable threshold:** Passed at run 122. Still pending.

---

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` monitors credential staleness and warns at >=76 days. It has NO escalation tier for imminent expiry (≤10 days remaining). Current behavior:

- Checks `days_since_rotation` >= 76d → adds comment to existing GH #399 thread
- Does NOT detect when `days_remaining <= 10` or file a P0-severity issue

**Critical state as of 2026-09-20:**
- AUTOPILOT_GH_TOKEN: rotated 2026-07-04, 78d elapsed, **expires 2026-10-02 (12 days away)**
- Brain connector PAT: same rotation date, same expiry
- P0 tier fires at day 80 (≤10d remaining) — fires **2026-09-22 (2 days from today)**
- grep in SKILL.md: `days_remaining` = 0 hits, `P0` = 0 hits — **P0 tier ABSENT**

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

7 consecutive carries (runs 119→120→121→122→123→124→125→126) prove:
1. The evidence is correct and consistent
2. The recommendation is precise and implementable
3. The urgency increases with each carry: AUTOPILOT_GH_TOKEN moves from "approaching" to "imminently expiring"
4. P0 threshold fires 2026-09-22 — 2 days. Each carry adds 1 day of urgency.

Run 122 reached the autonomous-executable mandate (3 carries). Runs 123→126 are 4th/5th/6th/7th carries. The task prompt constraint "Do NOT implement" continues to block execution. An interactive session is required to implement.

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

## What This Replaces

Runs 119-125 all recommended the same change (with run 125 carrying Step 9G instead). This is the 7th carry for Step 9E. The recommendation is identical — the evidence is fresher and the expiry is closer (12d remaining).

---

## Confidence

**HIGH** — Evidence consistent across 7 runs. Concrete expiry date (2026-10-02). P0 threshold fires 2026-09-22 (2 days). Implementation is a single SKILL.md block addition. No ambiguity in mechanism or target file.
