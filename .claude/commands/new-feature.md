---
description: Build a new feature end-to-end through the agent pipeline.
argument-hint: [feature description]
model: opus
---

Build a new feature end-to-end using the agent team. This command orchestrates the full pipeline.

## Step 1: Understand the Feature

Ask me ONE question if the request is ambiguous. Otherwise, proceed.

Determine:
- Does this feature need database changes?
- Does it need backend work?
- Does it need frontend work?
- Does it touch the widget?

## Step 2: Create a Session Checkpoint

Before starting any work, create a checkpoint file at `.claude/agent-comms/checkpoint.md` with:
- Feature name and description
- Which agents will be involved
- Planned order of operations
- Current date and time

This checkpoint survives compaction because it's on disk, not in conversation history.

## Step 3: Schema (if database changes needed)

Delegate to the **schema-guardian** agent:
- "Audit the current schema for [relevant tables]. Then design the migration needed for [feature]. Write your output to .claude/agent-comms/schema-guardian-output.md"

Read the output. If there are issues, resolve them before proceeding.

## Step 4: Backend (if API work needed)

Delegate to the **backend-dev** agent:
- Include the schema-guardian output in the prompt
- "Build the backend for [feature]. The schema-guardian confirmed [findings]. Write implementation summary to .claude/agent-comms/backend-dev-output.md"

## Step 5: Frontend (if UI work needed)

Delegate to the **frontend-dev** agent:
- Include the backend endpoints in the prompt
- "Build the frontend for [feature]. The backend provides these endpoints: [list]. Write summary to .claude/agent-comms/frontend-dev-output.md"

If frontend and backend are independent, run them in **parallel**.

## Step 6: Widget (if widget changes needed)

Delegate to the **widget-specialist** agent:
- "Update the widget for [feature]. Write summary to .claude/agent-comms/widget-specialist-output.md"

## Step 7: Test

Delegate to the **qa-tester** agent:
- Include all previous agent outputs
- "Validate the [feature] implementation. Check schema consistency, API correctness, frontend integration, and known bug patterns. Write results to .claude/agent-comms/qa-tester-output.md"

## Step 8: Document & Clean Up

1. If the feature added a new table or endpoint, update CLAUDE.md
2. If a bug was found and fixed during development, append to docs/dev-knowledge/bug-patterns.md
3. If the schema changed, append to docs/dev-knowledge/schema-log.md
4. Update the checkpoint file with completion status
5. Clean up .claude/agent-comms/ files (delete all except README.md and .gitkeep)

## Step 9: Commit

```
git add .
git commit -m "feat: [feature name] — [brief description]"
```

Report: what was built, which agents were used, any concerns for the developer to review.
