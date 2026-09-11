# Idea 4 — Step 9M: os_tool_executions.py God Class Split Recommendation

## Category
code_health

## Evidence
- os_tool_executions.py: 783 lines. Last commit: bc0332b (fix(voice): meter live-AI, ~2026-09-04). Stable 12+ days.
- Runs 116, 117, 118 all noted this file as "stable split candidate" — 4 consecutive runs
- CLAUDE.md Rule 9: files >600 lines → factor first, then add. Current: 183 lines over threshold.
- Services in the file span: voice calls, OS file ops, email sends, calendar ops, CRM actions — 5+ concerns in one module
- PR #792 (metering fix for os_tool_executions.py) had wide blast radius precisely because all tool types share one file
- check_ai_metering.py still finds violations in os_files.py (os_tool_executions.py split candidate) at _vision_describe

## Proposal
**Add Step 9M to `.claude/skills/nightly-commit-review/SKILL.md`:**

```
9M. (God Class Watch: os_tool_executions.py)
    Check line count: wc -l backend/services/os_tool_executions.py
    If > 600 lines AND last commit > 14 days ago:
      Search open GH issues: 'os_tool_executions split'
      If no open issue: create_issue(
        title='refactor(backend): split os_tool_executions.py god class (783L → voice/files/email/calendar modules)',
        labels=['refactor', 'backend', 'code-health'],
        body='File at [LINE_COUNT] lines (threshold: 600). Split into: os_voice_executions.py, os_file_executions.py, os_email_executions.py, os_calendar_executions.py. Reduces blast radius for future metering/routing changes.'
      )
    Else: Log 'Step 9M: os_tool_executions.py at [N] lines, [D] days stable. Monitoring.'
```

## Expected Impact
- Tracks the god class split in GH Issues where it can be assigned
- 4-consecutive-run evidence satisfies the evidence bar
- Step 9M is additive only (monitoring → issue filing when stable enough)

## Autonomous-executable
YES — SKILL.md edit, proven channel.
