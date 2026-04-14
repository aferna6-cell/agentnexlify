---
name: issue-to-pr-loop
description: "GitHub issue → PR automation loop. Polls issues assigned to you every 15min, classifies readiness, dispatches subagent, opens PR, handles review comments. Separate from and supersedes `autopilot-loop`."
version: 1.0.0
origin: aidan
license: MIT
user-invocable: true
triggers: ["issue to pr", "automate my issues", "issue loop", "auto pr", "full automation"]
allowed-tools: [Bash, Read, Write, Edit, Grep, Glob]
effort: high
---

# Issue → PR Loop

Full automation. Replaces `autopilot-loop`. Pattern: **classify → execute → PR feedback**.

## Flow

```
cron (15min)
  │
  ├── fetch issues assigned to @aferna6-cell (state:open, no wip-auto label)
  │
  ├── CLASSIFY (Haiku)
  │     ready? → label `auto-ready`, proceed
  │     not ready? → draft clarifying comment, label `needs-info`, stop
  │
  ├── EXECUTE (Sonnet subagent in worktree)
  │     1. branch `auto/issue-{N}-{slug}`
  │     2. read issue body + attachments + CLAUDE.md
  │     3. implement per karpathy-guidelines
  │     4. run tests + build
  │     5. commit, push, open PR linked to issue
  │     6. label issue `auto-pr`
  │
  └── PR FEEDBACK (separate cron, 10min)
        for each open auto-pr:
          new review comments? → Sonnet subagent implements, pushes
          tests red? → fix loop (max 3 retries)
          tests green + approved? → label `auto-ready-merge`
```

## Prereqs

1. `gh` CLI authenticated: `gh auth status`
2. Labels exist: `auto-ready`, `auto-pr`, `needs-info`, `auto-ready-merge`, `auto-failed`
3. Secret `ANTHROPIC_API_KEY` in env or `.env`
4. Branch protection on `main`: require PR + 1 review (prevents auto-merge footgun)
5. `scripts/automation/issue-to-pr.sh` cron installed

## Install

```bash
# create labels
for L in auto-ready auto-pr needs-info auto-ready-merge auto-failed; do
  gh label create "$L" --color "ededed" --force
done

# install cron (Linux/Mac)
( crontab -l 2>/dev/null; echo "*/15 * * * * cd $PWD && bash scripts/automation/issue-to-pr.sh >> logs/issue-loop.log 2>&1" ) | crontab -
( crontab -l 2>/dev/null; echo "*/10 * * * * cd $PWD && bash scripts/automation/pr-feedback.sh >> logs/pr-loop.log 2>&1" ) | crontab -

# Windows: use Task Scheduler pointing at Git Bash + the .sh files
```

## Classify prompt (Haiku)

```
You are a triage agent. Decide if this GitHub issue is ready for an AI subagent to implement end-to-end.

Return STRICT JSON:
  {"ready": true|false, "reason": "...", "clarifying_questions": ["..."]}

Ready criteria (ALL must hold):
- goal is concrete (one sentence describing desired behavior)
- files/paths or feature area identifiable
- success criteria stated or inferable from examples
- no open architectural decisions required
- no external credentials needed that aren't already in repo

Not-ready → provide 1-3 clarifying questions in JSON.
```

## Execute prompt (Sonnet worktree)

```
You implement ONE GitHub issue end-to-end. Follow project CLAUDE.md and karpathy-guidelines STRICTLY.

Required:
- think before coding (plan in scratchpad)
- surgical changes only (don't touch unrelated files)
- tests first for new behavior
- run: uvicorn backend.main:app --reload (backend); npm run build (frontend)
- commit message: `feat({scope}): {summary}\n\nCloses #{N}`
- open PR with body: issue link + test plan + files changed rationale
- on failure, push the attempt + label `auto-failed`, comment the stack

Forbidden:
- touching _archive/, landing-page-v2/, public/
- adding dependencies not in issue scope
- from __future__ import annotations
- localStorage in React
- tenant_id (use client_id) or lead_stage (use status) in leads table
```

## PR-feedback prompt (Sonnet)

```
Implement unresolved review comments on this PR. Rules:
- one commit per comment thread
- reply to the comment with the commit SHA
- if reviewer requests a larger change than the PR scope, reply with a scope question, don't implement
- re-run tests + build before pushing
```

## Safety

- **Human-in-loop merge** — branch protection blocks auto-merge; `auto-ready-merge` label signals "safe to squash"
- **Cost cap** — `ANTHROPIC_BUDGET_USD` env var; loop exits if exceeded
- **Retry cap** — max 3 attempts per issue, then `auto-failed` + notification
- **Scope guard** — subagent runs in isolated worktree; main working tree untouched
- **Rollback** — branch naming `auto/issue-{N}-...` makes mass-delete trivial: `git branch -D $(git branch | grep ^auto/)`

## Differences from autopilot-loop

| Dimension | autopilot-loop | issue-to-pr-loop |
|-----------|---------------|------------------|
| Trigger labels | `ai-ready` | `auto-ready` (auto-classified) |
| Classification | Manual label | Haiku classifier |
| Execution | Codex worktree | Sonnet worktree via `claude -p` |
| PR comments | Separate skill | Built-in |
| Cost model | Per-invocation | Budget-capped loop |
| Cron | GitHub Actions | Local cron (faster iter, no Actions minutes) |

## When to use

- You have a backlog of well-scoped issues
- You want to batch-process overnight
- You trust the test suite to catch regressions

## When NOT to use

- Issues touching auth, payments, schema, migrations → human-in-loop
- Issues requiring product decisions → classifier will return `needs-info`, good
- Repos without branch protection → turn it on first

## Scripts

- `scripts/automation/issue-to-pr.sh` — the 15-min loop
- `scripts/automation/pr-feedback.sh` — the 10-min loop
- `scripts/automation/classify-issue.sh` — Haiku classifier (called by loop)

## Tuning

- Start with `*/30 * * * *` (every 30min) until you trust it
- Set `MAX_CONCURRENT=1` in the script while observing
- Watch `logs/issue-loop.log` for 48h before raising concurrency
