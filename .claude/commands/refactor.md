Analyze and refactor code using the agent team. Safe, incremental improvements.

## Step 1: Scope the Refactor

Ask me what to refactor if not specified. Options:
- A specific file or directory
- A specific pattern (e.g., "fix all bare except blocks")
- A full codebase sweep for code quality

## Step 2: Create Checkpoint

Write checkpoint to `.claude/agent-comms/checkpoint.md` with refactor scope and goals.

## Step 3: Analyze

Delegate to **qa-tester**:
- "Analyze [scope] for code quality issues: bare excepts, dead imports, inconsistent patterns, missing error handling, duplicated code, TODO/FIXME items. Write findings to .claude/agent-comms/qa-tester-output.md"

## Step 4: Plan

Read the analysis. Create a refactoring plan ordered by:
1. Safety improvements (error handling, logging)
2. Dead code removal
3. Pattern consistency
4. Performance improvements

Do NOT plan changes to business logic. Only structural and quality improvements.

## Step 5: Execute

For each planned change:
1. Make the change
2. Verify the app still builds (frontend and backend)
3. If a build breaks, revert that specific change immediately

Use the backend-dev or frontend-dev agent as appropriate for each change.

## Step 6: Verify

Delegate to **qa-tester** for final validation.

## Step 7: Document

If any bugs were discovered during refactoring, log them in bug-patterns.md.

## Step 8: Clean Up & Commit

```
git add .
git commit -m "refactor: [scope] — [summary of improvements]"
```

Report: what was improved, files changed, any issues found.
