# Agent Communication Directory

This directory is the shared workspace where agents coordinate on multi-step tasks.

## How It Works

When the main Claude Code session delegates a complex task:

1. The orchestrator (main session) breaks the task into subtasks
2. Each agent writes its findings/output to a file here
3. The orchestrator reads outputs and routes to the next agent
4. Final results are compiled and presented to the developer

## File Naming Convention

Files follow the pattern: `{agent-name}-{task-type}.md`

Examples:
- `schema-guardian-audit.md` — schema audit results
- `backend-dev-implementation.md` — backend implementation plan
- `qa-tester-results.md` — test results
- `orchestrator-plan.md` — the task breakdown and delegation plan

## Lifecycle

Files in this directory are ephemeral — they exist for the duration of a task. The orchestrator cleans them up after the task is complete. They are gitignored so they never enter version control.
