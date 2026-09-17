# Winning Concept — Run 2026-09-17 (Run 121)

**Winner:** Step 9E Credential Expiry Escalation — Earlier Warning + GH Issue Filing
**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit in SKILL.md)
**Confidence:** HIGH
**Carry-forward count:** 2 (2nd carry-forward from runs 119→120→121)
**Autonomous-executable threshold:** 3 consecutive carries → run 122 fires autonomously

---

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` fires at `days_since_rotation >= 76`.
The `days_remaining <= 10` early-warning threshold from run 120 is NOT present (grep confirmed 0 results for both `days_remaining` and `<= 10` in Step 9E block).

**Today (2026-09-17):**
- AUTOPILOT_GH_TOKEN: 75 days since rotation (last rotated 2026-07-04)
- Threshold: 76d — fires tomorrow (2026-09-18)
- Expires: 2026-10-02 (15 days remaining)
- GH #399: exists, receives comments, but has NOT received the urgency-framed comment with "rotate by 2026-10-02"

**The gap:** Token at 75d. Threshold fires at 76d tomorrow. But without `days_remaining <= 10` window, there is no mechanism to fire a comment NOW with 15-day urgency.

**The risk:** If AUTOPILOT_GH_TOKEN expires on 2026-10-02, the autonomous loop dies. No nightly reviews, no issue-to-PR loop, no subconscious runs.

---

## Implementation

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block.

**Change threshold logic:**
```
# Current (fires only when >= 76 days):
if days_since_rotation >= 76:
    [GH issue search + comment/create — already present]

# New (fires also when <= 10 days remaining, with days_remaining in comment):
days_remaining = rotation_interval_days - days_since_rotation  # typically 90 - days_since
if days_since_rotation >= 76 OR days_remaining <= 10:
    # Dedup: search open issues by label "credential-rotation" + credential name
    # If existing open issue: add comment with current days_remaining and expiry date
    # If no open issue: create new issue
    comment_body = f"Step 9E automated update: {credential_name} at {days_since_rotation}d. {days_remaining}d remaining before expiry ({expiry_date}). ACTION REQUIRED: rotate in Railway → GitHub Secrets before {expiry_date}."
```

**Credentials to check:**
1. AUTOPILOT_GH_TOKEN — last_rotated: 2026-07-04, interval: 90d, expiry: 2026-10-02
2. Brain PAT — last_rotated: 2026-07-04, interval: 90d, expiry: 2026-10-02
3. SUPABASE_ACCESS_TOKEN — last_rotated: unknown

**Dedup guard (critical):** GH #399 is the existing AUTOPILOT_GH_TOKEN rotation issue. Search by label "credential-rotation" before creating a new issue. Comment on #399 rather than creating duplicate.

---

## Verification After Implementation

```bash
grep 'days_remaining' .claude/skills/nightly-commit-review/SKILL.md
grep '<= 10' .claude/skills/nightly-commit-review/SKILL.md
grep 'expiry_date\|expires' .claude/skills/nightly-commit-review/SKILL.md
```
All three must return results in Step 9E block.

Next nightly run (2026-09-18): Step 9E fires for AUTOPILOT_GH_TOKEN (76d >= 76d threshold AND days_remaining = 14 which is > 10, so only threshold fires; urgency comment with expiry date goes to GH #399).

---

## Runner-Up: Step 9G MCP Fix (Idea 2)

Step 9G self-healing trigger is broken (`gh workflow run` unavailable in headless sessions).
KB autopopulate is 22 days stale (threshold: 7d).
Fix: replace `gh workflow run kb-autopopulate.yml` with `mcp__github__actions_run_trigger(...)`.

Effort: XS. Independent of Step 9E.
**Recommend bundling with Step 9E implementation** — both are SKILL.md edits, independent, low risk.

---

## Run 122 Mandate

1. Verify Step 9E has `days_remaining` and `<= 10` in Step 9E block (grep check)
2. Did Step 9E fire on 2026-09-18 nightly? GH #399 comment added?
3. AUTOPILOT_GH_TOKEN rotated before 2026-10-02 (15 days)?
4. Brain PAT rotation: rotation issue filed?
5. Step 9G MCP fix: implemented?
6. AI metering violations: still at 45, growing, or decreasing?
7. **ESCALATION FLAG:** if Step 9E not implemented by run 122 → autonomous-executable (precedent: Steps 9F/9G/9I/9J/9K/9L)

---

## Escalation Path

- Run 119: 0th carry → first proposal
- Run 120 (2026-09-11-pm): 1st carry → RECOMMEND
- Run 121 (this run, 2026-09-17): 2nd carry → **RECOMMEND with escalation flag**
- Run 122: 3rd carry → autonomous-executable. Subconscious implements directly per established precedent. No human approval required for this change.
