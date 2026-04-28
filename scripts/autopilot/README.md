# Autopilot Issue Loop

This directory contains the GitHub Actions scripts for the issue-driven
autopilot loop. The loop classifies labeled issues, opens bot PRs for ready
work, and can address human review comments on those PRs. It never merges.

The durable workflow contract lives in `docs/AUTOPILOT_WORKFLOW.md`. The
classifier, Codex executor, and PR review handler load that contract into their
prompts so the issue loop behaves like a small Symphony-style state machine
instead of a one-off script.

## Labeling Issues

Add `ai-ready` to an open issue only when the issue has enough detail for an
agent to attempt it:

- Desired behavior or bug outcome.
- Acceptance criteria.
- Affected file paths or likely surface.
- Reproduction steps for bugs.
- Any tests or manual checks expected before PR review.

Do not label issues `ai-ready` when they need judgment around security,
billing, customer communications, legal exposure, or product strategy.

## State Labels

- `ai-ready`: the issue is in the autopilot queue.
- `needs-info`: the classifier found missing acceptance criteria, paths, or
  reproduction detail. Add the missing context as a new issue comment.
- `wip-autopilot`: a dispatch is in progress or a bot PR is open.
- `autopilot-failed`: dispatch failed and a human should inspect the issue
  comment.
- `autopilot-skipped`: classifier declined the issue as out of scope.
- `autopilot-pr`: PR was opened by the loop and review comments can be handled.

Routing labels from `docs/AGENT_ROUTING.md` can be added before future model
routing decisions:

- `ai-routine`: low-risk implementation or cleanup.
- `ai-docs`: docs, sales assets, playbooks, or skill wording.
- `ai-tests`: tests or test-only refactors.
- `ai-risky`: premium-only work. Autopilot will not dispatch these issues.

## State Machine

```text
open issue
   |
   | add ai-ready
   v
queued for classifier
   |
   +--> NEEDS_INFO ---- add needs-info ----+
   |                                      |
   | Aidan adds issue comment             |
   +--------------------------------------+
   |
   +--> OUT_OF_SCOPE -- add autopilot-skipped -- stop
   |
   +--> READY -------- add wip-autopilot
                          |
                          v
                    Codex worktree dispatch
                          |
              +-----------+-----------+
              |                       |
              v                       v
        pre-commit fails        commit + push branch
              |                       |
              v                       v
     add autopilot-failed       open autopilot-pr
                                      |
                                      v
                            Aidan reviews manually
```

## Pausing The Loop

Disable either workflow from the GitHub Actions UI:

1. Open Actions.
2. Select `Autopilot Issue Loop` or `Autopilot PR Review Handler`.
3. Choose `Disable workflow`.

To pause one issue without disabling the workflow, remove `ai-ready` before it
is dispatched. To stop retrying a failed issue, leave `autopilot-failed` in
place until a human has inspected it.

## Manual Invocation

Use `workflow_dispatch` from the Actions UI:

1. Open Actions.
2. Select `Autopilot Issue Loop`.
3. Click `Run workflow` on the default branch.

For local smoke checks that do not mutate GitHub, run:

```bash
npm run autopilot:dry-run
npm run autopilot:dry-run:issue -- 1
```

Dry-run mode still needs `gh` installed and authenticated plus
`ANTHROPIC_API_KEY` in the local environment. It classifies issues but does not
label, dispatch Codex, push branches, comment, or open pull requests.

Pair dry-run checks with the local release gate while Actions minutes are
paused:

```bash
npm run check:local-release
```

## Cost Model

Classifier calls use Haiku and are tiny, usually under one cent for a normal
run. Dispatch and review handling route implementation through Sonnet-grade
execution and are the meaningful cost drivers. The scripts read a per-run token
budget from the runner environment, defaulting to `200000`, and abort if direct
Anthropic SDK calls exceed that budget.

The Codex subprocess does not expose token usage to these scripts, so treat
PR count and review-comment iterations as the practical spend controls:

- Issue loop dispatches at most one issue per cron tick.
- Issue loop dispatches only while open `wip-autopilot` issues are below
  `AUTOPILOT_MAX_ACTIVE_RUNS`, defaulting to `1`.
- Review handler stops after five bot commits on a PR.
- Every generated PR still requires human review and merge.

## Proof Of Work

Every autopilot PR body includes:

- Source issue link.
- Classifier reason and proposed plan.
- Changed file summary.
- Local verification command and pass/fail result.
- Workflow contract path.
- Residual risk notes for human review.

## Revoking The Bot Token

In an emergency:

1. Disable both workflows.
2. Revoke or rotate the fine-grained bot PAT in GitHub developer settings.
3. Remove or replace the matching repository secret.
4. Close or delete any untrusted bot branches and PRs.
5. Re-enable workflows only after confirming the replacement token has
   contents, issues, and pull request write access limited to this repository.

## Labels To Create

```bash
gh label create ai-ready --color 0e8a16 --description "Autopilot may attempt this issue"
gh label create needs-info --color fbca04 --description "Autopilot flagged as needing more context"
gh label create wip-autopilot --color 1d76db --description "Autopilot actively working on this issue"
gh label create autopilot-failed --color b60205 --description "Autopilot dispatch failed - manual intervention needed"
gh label create autopilot-skipped --color cccccc --description "Autopilot declined as out of scope"
gh label create autopilot-pr --color 5319e7 --description "PR was opened by autopilot"
gh label create ai-routine --color 0e8a16 --description "Low-risk task for future low-cost agent routing"
gh label create ai-docs --color 0075ca --description "Documentation task for future low-cost agent routing"
gh label create ai-tests --color d4c5f9 --description "Test task for future low-cost agent routing"
gh label create ai-risky --color b60205 --description "Premium-only task, do not dispatch autonomously"
```
