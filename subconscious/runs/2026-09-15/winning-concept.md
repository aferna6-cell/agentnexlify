# Winning Concept — Run 2026-09-15 (Run 121)

**Winner:** Step 9E Credential Expiry Escalation — days_remaining ≤10 threshold + GH comment filing
**Category:** workflow_efficiency / operational
**Effort:** XS (single SKILL.md block edit)
**Confidence:** HIGH
**Carry-forward count:** 2 (2nd carry-forward from run 119, 1st carry-forward from run 120)
**Autonomous-executable threshold:** run 122 (3rd carry-forward = direct implementation per Steps 9F/9G/9I/9J/9K/9L precedent)

---

## Recommendation

Extend Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` to fire at `days_remaining <= 10` (instead of `days_since_rotation >= 76`) and comment on the existing tracking GH issue rather than only logging to nightly markdown.

---

## Why This, Why Now

AUTOPILOT_GH_TOKEN expires 2026-10-02 (17 days). Step 9E checked it today and reported "0 approaching expiry" because 73 days < 76-day threshold — correct under current logic, but the proposed `days_remaining <= 10` threshold would have fired 7 days ago. The critical gap: current Step 9E only logs to nightly markdown; no GH issue is filed, no email notification sent. GH #399 has been open 73 days with no new comment — it appears dormant to the human. A fresh comment with "17 days to expiry" creates an email notification that the static nightly log does not. If AUTOPILOT_GH_TOKEN expires unrotated, the autonomous issue loop (Step 9D) and all ai-ready issue processing die until a human rotates it.

---

## Implementation Sketch

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block:

**1. Change threshold logic:**
```
# Remove:
if days_since_rotation >= 76:
    log_warning(...)

# Replace with:
days_remaining = threshold_days - days_since_rotation  # threshold_days = 76
if days_remaining <= 10:
    # ... file/comment logic below
```

**2. Add GH issue comment/filing logic:**
```
# Dedup: search for existing open issue labeled credential-rotation for this credential
existing_issues = mcp__github__search_issues(
    query=f"repo:aferna6-cell/agentnexlify is:open label:credential-rotation {credential_name_slug}"
)

if existing_issues and len(existing_issues) > 0:
    # Comment on the existing issue (don't create duplicate)
    mcp__github__add_issue_comment(
        issue_number=existing_issues[0].number,
        body=f"Step 9E automated update: **{credential_name}** is at {days_since_rotation}d since last rotation. **{days_remaining}d remaining** before {threshold_days}d threshold (expires ~{expiry_date}). Action required: rotate in Railway → GitHub Secrets and update ops/credential-rotation-schedule.md."
    )
else:
    # Create new issue
    mcp__github__issue_write(
        title=f"Credential rotation required: {credential_name} ({days_remaining}d remaining)",
        body=f"...",
        labels=["credential-rotation", "human-action-required", "ops"]
    )
```

**3. Add unknown-state handling:**
```
elif last_rotated == "unknown":
    # Search for existing open issue for this credential's unknown state
    existing = mcp__github__search_issues(
        query=f"repo:aferna6-cell/agentnexlify is:open label:credential-rotation label:needs-human-input {credential_name_slug}"
    )
    if not existing:
        mcp__github__issue_write(
            title=f"Credential rotation date unknown: {credential_name} — verify in dashboard",
            body=f"Step 9E cannot alert on expiry for {credential_name} because last_rotated is not set in ops/credential-rotation-schedule.md. Check the service dashboard, confirm the date, and update the schedule file.",
            labels=["credential-rotation", "needs-human-input", "ops"]
        )
```

**4. Update Step 9E log line:**
```
# Step 9E: {N} credentials checked, {M} approaching expiry (days_remaining ≤ 10), {K} unknown state, {J} GH actions taken
```

**5. Verification after implementation:**
```bash
grep 'days_remaining' .claude/skills/nightly-commit-review/SKILL.md
grep '<= 10' .claude/skills/nightly-commit-review/SKILL.md
grep 'add_issue_comment' .claude/skills/nightly-commit-review/SKILL.md
```
All three must return results in the Step 9E block.

---

## What This Replaces

Previous active direction: Step 9E fires at `days_since_rotation >= 76` and logs only. New direction: Step 9E fires at `days_remaining <= 10` and creates GH notification (comment or new issue).

---

## Run 122 Mandate

1. Verify `days_remaining` and `<= 10` threshold present in Step 9E: `grep 'days_remaining' .claude/skills/nightly-commit-review/SKILL.md` — should return results inside the Step 9E block.
2. Did Step 9E fire on next nightly? GH #399 should have a new comment from Step 9E.
3. AUTOPILOT_GH_TOKEN: rotated before 2026-10-02? (Now 17 days away.)
4. Brain PAT: same state as AUTOPILOT_GH_TOKEN — rotated?
5. SUPABASE_ACCESS_TOKEN: GH issue filed for unknown state?
6. **Step 9G MCP fix** (run 121 Parking Lot A): verify kb-autopopulate.yml has `workflow_dispatch:` trigger; verify `mcp__github__actions_run_trigger` available in nightly CCR sessions; implement if both confirmed.
7. **Step 9L dedup fix** (run 121 Parking Lot B): implement systemic-label search before filing duplicate summary issue.

---

## Escalation Path

- Run 119: proposed (1st recommendation)
- Run 120: 1st carry-forward → RECOMMEND
- Run 121 (this run): 2nd carry-forward → RECOMMEND with escalation flag
- **Run 122: 3rd carry-forward = autonomous-executable** (precedent: Steps 9F/9G/9I/9J/9K/9L all auto-implemented on 3rd carry-forward)
- If token expires before run 122: run 122 implements directly per autonomous-executable governance.

---

## Confidence: HIGH

Evidence: 3 consecutive nightlies logged warning, zero human action. AUTOPILOT_GH_TOKEN expires in 17 days. Dedup guard handles GH #399. Implementation is XS effort (SKILL.md block edit only). Same autonomous-executable channel as prior Steps.
