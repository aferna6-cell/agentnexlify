---
description: Recover context after compaction or a session restart from the checkpoint.
model: sonnet
---

Recover context after compaction or a session restart.

## Step 1: Read the Checkpoint

Read `.claude/agent-comms/checkpoint.md` if it exists. This contains:
- What we were working on
- Decisions made
- Files modified
- Current status
- Next steps

## Step 2: Read Recent Agent Outputs

Check for any agent output files in `.claude/agent-comms/`:
- schema-guardian-output.md
- backend-dev-output.md
- frontend-dev-output.md
- widget-specialist-output.md
- qa-tester-output.md
- devops-output.md

Summarize what each agent found/did.

## Step 3: Read Recent History

Check:
- `git log --oneline -10` for recent commits
- `git diff --stat` for uncommitted changes
- `docs/daily-logs/current-tasks.md` for the task backlog

## Step 4: Restore Context

Based on everything above, provide a concise summary:
- "Here's where we left off: [summary]"
- "The next step is: [next step]"
- "These files have uncommitted changes: [list]"

Ask: "Ready to continue, or do you want to change direction?"
