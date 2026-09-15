# Idea 1 — Step 9E Credential Expiry Escalation: Earlier Warning + GH Issue Filing

**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit in SKILL.md)
**Confidence:** HIGH
**Status:** WINNER (2nd carry-forward from run 119)

---

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` tracks credential rotation age. Current logic:
- Fires when `days_since_rotation >= 76` (4 days before 90d interval)
- Logs to nightly markdown file only
- Does NOT file a GH issue proactively
- Does NOT alert before reaching the 76d threshold

Evidence from today's nightly (2026-09-15):
- AUTOPILOT_GH_TOKEN: 73d since rotation — threshold 76d fires in 3 days
- The 10-day early warning window (days 66-76) was completely silent
- No GH issue filed, no alert, no notification
- 3 consecutive runs (119, 120, 121) recommended this fix — not implemented

If AUTOPILOT_GH_TOKEN is not rotated by 2026-10-02, the autonomous loop dies.

---

## Implementation

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block.

**Add earlier threshold:**
```
# Current: fires at days_since_rotation >= 76 (too late)
# New: ALSO fires at days_remaining <= 10 (days_remaining = 76 - days_since_rotation)

days_remaining = threshold_days - days_since_rotation  # threshold_days = 76
if days_remaining <= 10:  # fires at 66+ days since rotation (10 days before threshold)
    # Dedup: search open issues by label "credential-rotation" + credential name
    # If existing open issue: add comment with current days_remaining
    # If no open issue: create new issue
    mcp__github__search_issues(query="repo:aferna6-cell/agentnexlify is:open label:credential-rotation {credential_name}")
    if existing_issue:
        mcp__github__add_issue_comment(issue_number=existing_issue.number,
            body=f"Step 9E automated update: {credential_name} at {days_since_rotation}d since rotation. {days_remaining}d remaining before {threshold_days}d threshold. Expires ~{expiry_date}. Action required.")
    else:
        mcp__github__issue_write(title=f"Credential rotation required: {credential_name}",
            body=..., labels=["credential-rotation", "human-action-required", "ops"])
```

**Credentials to check:**
1. AUTOPILOT_GH_TOKEN — last_rotated: 2026-07-04, interval: 90d, threshold: 76d
2. Brain PAT — last_rotated: 2026-07-04, interval: 90d, threshold: 76d
3. SUPABASE_ACCESS_TOKEN — last_rotated: unknown

**Dedup guard (critical):** GH #399 is the existing AUTOPILOT_GH_TOKEN rotation issue. Comment on it rather than creating a duplicate.

---

## Evidence

- Today's nightly: 73d since rotation, 0 Step 9E alerts — proves the 10-day window was missed
- Run 119 winner: 1st carry-forward
- Run 120 winner: 2nd carry-forward
- Governance mandate: autonomous-executable at run 122
- AUTOPILOT_GH_TOKEN expires 2026-10-02 (17 days from today)

---

## Verification

```bash
grep 'days_remaining' .claude/skills/nightly-commit-review/SKILL.md
grep '<= 10' .claude/skills/nightly-commit-review/SKILL.md
grep 'add_issue_comment' .claude/skills/nightly-commit-review/SKILL.md
```

All three must return results in Step 9E block.
