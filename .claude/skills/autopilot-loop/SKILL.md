---
name: autopilot-loop
description: Configure and operate the GitHub issue autopilot loop that classifies ai-ready issues, dispatches Codex worktrees, opens PRs, and handles autopilot PR review comments. Use when user says 'set up autopilot', 'enable autonomous loop', 'autopilot loop', 'issue autopilot', 'autonomous issue loop', or asks about autopilot loop.
version: 1.0.0
origin: claude
user_invocable: true
allowed_tools:
- Read
- Write
- Edit
- Bash
- Glob
- Grep
triggers:
- set up autopilot
- enable autonomous loop
- autopilot loop
- issue autopilot
- autonomous issue loop
effort: high
---

# Autopilot Loop

Use this skill when the user wants to configure, inspect, or operate the
GitHub-issue-driven autopilot loop for AgentNexLiFy.

## Prereq Checklist

Before enabling the loop, verify:

1. Repository labels exist: `ai-ready`, `needs-info`, `wip-autopilot`,
   `autopilot-failed`, `autopilot-skipped`, `autopilot-pr`.
2. Repository secrets exist: `ANTHROPIC_API_KEY` and `AUTOPILOT_GH_TOKEN`.
3. The bot token is fine-grained and limited to this repo with contents,
   issues, and pull request write access.
4. GitHub Actions are enabled for
   `.github/workflows/autopilot-issue-loop.yml`.
5. GitHub Actions are enabled for
   `.github/workflows/autopilot-pr-review.yml`.
6. `codex` is available on the runner path, or dispatch will fail with a clear
   issue comment.
7. Aidan is ready to review every autopilot PR manually. No auto-merge exists.

## Operating Rules

- Add `ai-ready` only to issues with concrete acceptance criteria.
- Do not label security, billing, customer communications, legal, or broad
  strategy issues as `ai-ready`.
- Leave `autopilot-failed` in place until a human has inspected the failure.
- Remove `ai-ready` to pull an issue out of the queue.
- Disable the workflow from GitHub Actions to pause globally.

## Seven Gotchas

1. Concurrency races: the issue workflow is serialized globally, and the PR
   handler is serialized per PR. Do not remove those concurrency groups.
2. Label-state pitfalls: `wip-autopilot` is the mutex. Removing it while a run
   is active can duplicate dispatch.
3. Runaway cost loops: review handling stops after five bot commits per PR, but
   the Codex subprocess still has external spend. Watch PR volume.
4. PR spam: low-quality `ai-ready` labels create low-quality PRs. The label is
   the human gate.
5. Pre-commit loops: failed pre-commit adds `autopilot-failed`; do not clear it
   without fixing the root cause or adding more issue context.
6. Bot rate limits: if the fine-grained PAT hits API limits, the loop fails
   loudly in Actions and issue comments. Let the token cool down or rotate it.
7. Issue-comment hash collisions: the loop uses full SHA-256 markers, not
   truncated hashes. Do not shorten `<!-- autopilot-state:... -->` markers.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Stuck in `wip-autopilot` | Dispatch started but workflow failed before PR creation | Read the workflow log, remove `wip-autopilot` only after confirming no PR/branch is active, then decide whether to retry. |
| `autopilot-failed` with no useful error | The failure happened before the script could post a detailed comment | Inspect the GitHub Actions log for the run and verify the bot token, `codex`, and Python dependencies. |
| PR branch conflicts `main` | Human changes landed after autopilot opened the PR | Rebase or close the bot PR manually; do not rely on the PR handler for branch maintenance. |
| No classifier comments | Issue is missing `ai-ready`, workflow disabled, or token lacks issue write access | Check labels, workflow state, and token permissions. |
| Review comment ignored | PR lacks `autopilot-pr`, commenter is the bot, or max review iterations reached | Add the label only for trusted bot PRs or handle manually after the cap. |

## Manual Commands

Dry-run a single issue:

```bash
python3 scripts/autopilot/classify_and_dispatch.py --dry-run --issue 1
```

Run the issue loop locally:

```bash
python3 scripts/autopilot/classify_and_dispatch.py
```

Run the workflow manually:

```bash
gh workflow run autopilot-issue-loop.yml
```
