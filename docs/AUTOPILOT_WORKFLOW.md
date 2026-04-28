# Agent Nexlify Autopilot Workflow

This document is the repo-owned workflow contract for autonomous issue work.
The autopilot scripts load this file into classifier, implementation, and
review-comment prompts so agent behavior is versioned with the codebase.

## Purpose

Use the GitHub issue tracker as the control plane for routine, well-scoped
engineering work. Autopilot may classify issues, create isolated worktrees,
dispatch Codex, open pull requests, and address review comments. Humans retain
review, merge, product judgment, and final release authority.

## Eligible Work

Autopilot may work on an issue when all of these are true:

- The issue has the `ai-ready` label.
- Desired behavior, acceptance criteria, and likely surface are clear.
- The change can be implemented and verified in one focused PR.
- Required credentials, services, and test data are already available to the repo.
- The work can be reviewed from a PR without extra private context.

## Ineligible Work

Autopilot must decline or ask for clarification when work involves:

- Auth, payments, billing, pricing, legal exposure, or customer communications.
- Database migrations, destructive data changes, or schema changes without an explicit plan.
- Secrets, production credentials, or third-party account setup.
- Broad product strategy, unclear UX decisions, or ambiguous acceptance criteria.
- Large rewrites, dependency upgrades, or cross-surface refactors not requested by the issue.

## State Machine

Use GitHub labels as the durable state machine:

| State | Label | Meaning |
| --- | --- | --- |
| Queued | `ai-ready` | Issue is eligible for classifier review. |
| Needs information | `needs-info` | The issue lacks enough context for autonomous work. |
| Active | `wip-autopilot` | A dispatch is running or a bot PR is waiting for review. |
| Failed | `autopilot-failed` | A dispatch failed and needs human inspection. |
| Skipped | `autopilot-skipped` | The classifier declined the issue as out of scope. |
| PR open | `autopilot-pr` | A pull request was opened by the autopilot loop. |

Autopilot should run with bounded concurrency. The default active-run cap is
one open `wip-autopilot` issue unless `AUTOPILOT_MAX_ACTIVE_RUNS` overrides it.

## Workspace Rules

- Use a fresh git worktree per issue.
- Keep the main checkout untouched.
- Keep changes scoped to the issue and classifier plan.
- Do not commit, push, label, or open a PR from inside Codex; the script owns those actions.
- Preserve user-authored or unrelated changes.
- Clean up the worktree after dispatch completes or fails.

## Proof Of Work

Every autopilot PR body must include:

- Source issue link.
- Classifier reason and proposed plan.
- Changed file summary.
- Local verification command and pass/fail result.
- Workflow contract path.
- Human review notes, including skipped checks or residual risks.

For UI-facing changes, attach screenshots or walkthrough media when the runner
has browser tooling available. Otherwise, state that visual verification still
needs human review.

## Human Review Rules

- Autopilot never merges.
- Branch protection must require PR review before merge.
- Review-comment handling must stay scoped to the comment thread.
- Larger reviewer requests should become a new issue instead of silently
  broadening the PR.
- Failed runs should leave a concise issue comment with the first actionable
  error and enough context for a human to resume.
