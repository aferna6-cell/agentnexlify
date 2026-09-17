# Idea 5 — Step 9D: Stale ai-ready Issue Escalation

**Category:** workflow_efficiency / operational
**Effort:** XS (Step 9D block edit in SKILL.md)
**Confidence:** MEDIUM

## Problem

Step 9D monitors issues labeled `ai-ready` for the autopilot loop.
When issues are closed by owner (#870, #875 both closed 2026-09-16),
Step 9D reports "closed — monitoring continues" but takes no further action.

Pattern: owner closes issues → loop has no new ai-ready issues → loop stalls.
No mechanism to surface "autopilot loop is idle" to owner.

Evidence (2026-09-17.md):
- Step 9D: #870 and #875 closed. No new ai-ready issues observed.
- No escalation filed. No GH comment nudging owner to add new ai-ready issues.

## Implementation

Add staleness counter to Step 9D in `.claude/skills/nightly-commit-review/SKILL.md`:

```
if open_ai_ready_issues == 0 AND days_since_last_ai_ready_closed >= 3:
    # Search for issues matching ai-ready criteria but not yet labeled
    # Comment on last-closed ai-ready issue: "Loop idle N days. Consider labeling new issues."
    mcp__github__add_issue_comment(issue_number=last_closed_issue, body=f"...")
```

Dedup guard: only one comment per 7-day window (check comment history before posting).

## Expected outcome

- Owner alerted when autopilot loop is idle for 3+ days
- Comment on a relevant (recently closed) issue, not a new one
- Nudges owner to label new issues ai-ready without creating noise

## Risk

LOW. Comment-only. Dedup guard prevents spam. Reversible.

## Notes

Lower urgency than Step 9E (credentials) and Step 9G (KB stale).
Addresses idle loop signal gap. Good companion to existing Step 9D.
