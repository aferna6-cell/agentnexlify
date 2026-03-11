Diagnose and fix a bug using the agent team. Optimized for speed — find it, fix it, document it.

## Step 1: Understand the Bug

Ask me to describe the symptom if I haven't already. Key questions:
- What's the expected behavior?
- What's actually happening?
- Any error messages?
- Which part of the app is affected (widget, dashboard, API, signup)?

## Step 2: Check Known Patterns First

Read `docs/dev-knowledge/bug-patterns.md`. Is this a known bug or a variation of one? If yes, apply the documented fix immediately — don't rediscover it.

## Step 3: Create a Session Checkpoint

Write a checkpoint at `.claude/agent-comms/checkpoint.md`:
- Bug description
- Suspected area (backend/frontend/widget/schema)
- Relevant files to investigate

## Step 4: Diagnose

Based on the symptoms, delegate to the right specialist:

| Symptom | Agent | Skill |
|---------|-------|-------|
| 422 error, data not saving | schema-guardian | schema-guard |
| API error, 500, endpoint failing | backend-dev | debug-api |
| UI broken, page not loading | frontend-dev | — |
| Widget not working, CORS error | widget-specialist | widget-test |
| Not sure / multiple areas | qa-tester (to diagnose) | debug-api |

The diagnosing agent writes findings to `.claude/agent-comms/{agent}-output.md`.

## Step 5: Fix

Delegate the fix to the appropriate implementation agent (backend-dev, frontend-dev, or widget-specialist). Include the diagnosis in the prompt.

## Step 6: Verify

Delegate to **qa-tester**:
- "Verify the fix for [bug]. Check for regressions. Run build checks. Write results to .claude/agent-comms/qa-tester-output.md"

## Step 7: Document

This is mandatory — append to `docs/dev-knowledge/bug-patterns.md`:
- Symptom
- Root cause
- Fix applied
- Files changed
- Prevention strategy

If the bug was schema-related, also update `docs/dev-knowledge/schema-log.md`.

## Step 8: Clean Up & Commit

Clean up .claude/agent-comms/ and commit:
```
git add .
git commit -m "fix: [short description of what was fixed]"
```

Report: what the bug was, root cause, what was fixed, files changed.
