# Spec — Autonomous GitHub issue loop (solo-founder autopilot)

**Status:** Draft · 2026-04-11
**Owner:** Aidan
**Related:** `.claude/skills/build-loop/SKILL.md`, `.claude/skills/worktree-orchestrator/SKILL.md`, `.claude/skills/compound-engineering/SKILL.md`, `scripts/managed_agents/field_monitor_run.py`, codex:rescue skill
**Priority:** P3 (nice-to-have, not blocking revenue)

## Problem

Article reference: engineer built a .NET app that polls GitLab every 15 min, classifies assigned issues via Claude, auto-implements ready ones into draft PRs, and monitors PRs for new review comments to implement them. 8 hrs coding → 2-3 hrs reviewing.

Transpose to agentnexlify reality:

- **Not employed.** No mouse-wiggler / Teams-inactivity hack needed. Solo founder.
- **Bug/feature backlog lives in GitHub Issues** (`aferna6-cell/agentnexlify`) + `.claude/agent-comms/backlog.md`.
- **1 open issue** as of 2026-04-11 (#1 critical automation_engine.py truncation). Low issue volume — backlog discipline not yet established.
- **Existing automation doesn't touch issues.** `build-loop` skill reads `.claude/agent-comms/backlog.md` (manual file). `subconscious` agent runs self-improvement cycles but doesn't dispatch to issues. Daily routines (`morning`, `evening`) summarize state but don't build.

Gap: **no bridge between GitHub Issues and the existing autonomous-build infrastructure**. The article's pattern (issue → classify → dispatch → PR → review-loop) would close that gap.

## Goal

Ship a 15-min cron that polls open `ai-ready`-labeled GitHub issues, classifies each with Claude, dispatches ready ones to Codex or compound-engineering for implementation on a new branch + PR, and addresses PR review comments on subsequent cron ticks. Aidan reviews every PR manually before merge — the automation never merges on its own.

## Non-goals

- **Replacing human review.** Every PR from the autopilot goes through Aidan's normal review + merge flow. No auto-merge.
- **Replacing `build-loop`.** That reads a manual backlog and is useful for proactive feature work that has no issue. This spec is for reactive issue-driven work.
- **Mouse-wiggler / anti-inactivity hacks.** Solo founder. No Teams.
- **Replacing `compound-engineering`.** The autopilot delegates to it for ready issues.
- **Supporting private issues from other repos.** Scope is `aferna6-cell/agentnexlify` only.

## Architecture decisions

1. **GitHub Actions as the cron, not Railway.** Issues live in GitHub — putting the poller in GitHub Actions puts the poller next to its data source. Zero Railway backend changes. Secrets (`ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`) go into repo secrets.
2. **Issue label is the trigger.** `ai-ready` label on an open issue = "autopilot may attempt". `needs-info` label = classifier already flagged + waiting on Aidan. `wip-autopilot` label = PR open, don't re-dispatch. This makes the state machine visible in GitHub UI, no separate DB needed.
3. **Classifier runs on every tick, idempotent.** Reads issue body + any Aidan-added comments since last classification. If ready, transitions to `wip-autopilot` + dispatch. If not, posts a draft comment explaining what's unclear and adds `needs-info`. Comment includes a hash of the issue state so re-classification doesn't post duplicate comments.
4. **Dispatcher uses Codex CLI, not raw Anthropic API.** Codex's write mode + sandbox restrictions match what the existing `codex:rescue` skill already delivers. Leverages sunk infrastructure.
5. **Dispatcher runs in a fresh `git worktree`, not the main workspace.** `worktree-orchestrator` skill pattern. Branch name: `autopilot/issue-{number}-{slug}`. Isolation prevents autopilot runs from stepping on Aidan's uncommitted work.
6. **PR author is a bot identity, not Aidan.** Use a `AUTOPILOT_GH_TOKEN` (fine-grained PAT or separate bot account) so PRs are visibly "from autopilot" and don't pollute Aidan's contribution history.
7. **PR comment watcher uses `pull_request_review_comment` webhook event, not polling.** Real-time. Separate workflow file. Triggers when Aidan comments on an autopilot PR → spawns Codex to address.
8. **Hard cost + time budget per cycle.** 15-min poll tick can spawn at most 1 dispatch. Each dispatch caps at $2 of Anthropic spend via the existing managed-agents spend-tracker. If budget exceeded, cycle pauses + Slack alert (or email to `help@agentnexlify.com` for now).
9. **Stop if pre-commit fails.** Autopilot commits go through the same pre-commit hook as Aidan's. A failed gate (`__future__`, secrets, bare except) aborts the dispatch, posts the error to the issue, adds `autopilot-failed` label, removes `wip-autopilot`. No silent failures.

## Files to create

### 1. `.github/workflows/autopilot-issue-loop.yml` — NEW

```yaml
name: Autopilot Issue Loop
on:
  schedule:
    - cron: "*/15 * * * *"  # every 15 min
  workflow_dispatch:        # manual trigger for testing

concurrency:
  group: autopilot-issue-loop
  cancel-in-progress: false  # never interrupt a running dispatch

jobs:
  classify-and-dispatch:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install anthropic httpx
      - name: Run classifier + dispatcher
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          AUTOPILOT_GH_TOKEN: ${{ secrets.AUTOPILOT_GH_TOKEN }}
          GH_TOKEN: ${{ secrets.AUTOPILOT_GH_TOKEN }}
        run: python scripts/autopilot/classify_and_dispatch.py
```

### 2. `.github/workflows/autopilot-pr-review.yml` — NEW

```yaml
name: Autopilot PR Review Handler
on:
  pull_request_review_comment:
    types: [created]

jobs:
  handle-comment:
    if: contains(github.event.pull_request.labels.*.name, 'autopilot-pr') && github.event.comment.user.login != github.event.pull_request.user.login
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.ref }}
          token: ${{ secrets.AUTOPILOT_GH_TOKEN }}
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install anthropic
      - name: Implement review comment
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ secrets.AUTOPILOT_GH_TOKEN }}
        run: python scripts/autopilot/implement_review_comment.py
```

### 3. `scripts/autopilot/classify_and_dispatch.py` — NEW

**Responsibilities:**

1. `gh issue list --label ai-ready --state open --json number,title,body,labels,comments` to fetch candidates.
2. For each issue, skip if `wip-autopilot` or `needs-info` label already set (unless Aidan added new comments since last classification — detect via hash stored in a marker comment).
3. Call Claude Haiku (`claude-haiku-4-5-20251001`) with system prompt: "Classify this GitHub issue as READY, NEEDS_INFO, or OUT_OF_SCOPE. READY means implementation requirements are clear enough for a Sonnet executor to complete autonomously. NEEDS_INFO means the issue is missing acceptance criteria, reproduction steps, or affected file paths. OUT_OF_SCOPE means the issue requires human judgment (security, billing, customer communications, legal). Respond JSON-only: `{classification, reason, needed_info?, proposed_plan?}`."
4. If `NEEDS_INFO`: post comment with `needed_info` message + `<!-- autopilot-state:{hash} -->` marker, apply `needs-info` label.
5. If `OUT_OF_SCOPE`: post comment explaining why, apply `autopilot-skipped` label, never retry.
6. If `READY`: apply `wip-autopilot` label, invoke dispatcher subprocess (see step 7).
7. Dispatcher: create branch `autopilot/issue-{number}-{slug}`, write prompt file with issue body + `proposed_plan`, invoke `codex exec --write` (via codex-companion helper) pointing at the prompt file, wait for Codex completion.
8. Post-dispatch: `git status` check. If no changes → post failure comment + `autopilot-failed` label. If changes → run `scripts/hooks/pre-commit` manually. If passes → commit, push, `gh pr create` with `autopilot-pr` label referencing the issue.

**Cap per tick:** 1 dispatch. Additional ready issues queued for next tick. Prevents thrashing.

**Idempotency:** the `<!-- autopilot-state:HASH -->` marker in the most recent autopilot comment records which issue-state we've seen. If the hash matches current state, skip. If it differs (Aidan added info), re-classify.

### 4. `scripts/autopilot/implement_review_comment.py` — NEW

**Responsibilities:**

1. Parse `pull_request_review_comment` payload from `$GITHUB_EVENT_PATH`.
2. Extract: PR branch, comment body, file path + line number of the comment.
3. Fetch surrounding code context (10 lines before + after).
4. Call Sonnet with: "A human reviewer left this comment on the PR. Implement the requested change. Touch only the file and surrounding context unless the change requires edits elsewhere." + context block.
5. Apply via `codex exec --write` on the branch workspace.
6. If diff non-empty → run pre-commit → commit with message `autopilot: address review comment on {file}:{line}` → push.
7. Reply to the review comment thread: "Addressed in {sha}" on success, or "Failed: {reason}" on error.

**Concurrency:** multiple review comments on the same PR land in parallel runs. Use `concurrency: group: autopilot-pr-${pr_number}` to serialize per-PR.

### 5. `scripts/autopilot/README.md` — NEW

Operator doc explaining:

- How to label an issue `ai-ready`
- How to interpret `needs-info` vs `wip-autopilot` vs `autopilot-failed` vs `autopilot-skipped` vs `autopilot-pr`
- How to pause the loop (disable the workflow via GitHub UI)
- How to run manually (`workflow_dispatch`)
- Budget limits + where spend is logged
- How to revoke the `AUTOPILOT_GH_TOKEN` in an emergency

### 6. `.claude/skills/autopilot-loop/SKILL.md` — NEW

Wrapper skill that teaches Claude how to configure this when the user says "set up autopilot" or "enable autonomous loop". Contains:

- Prereq checklist (labels exist, secrets set, bot token valid)
- 7 gotchas (concurrency races, label-state machine pitfalls, runaway cost loops, PR spam, pre-commit infinite loops, bot rate limits, issue-comment hash collision)
- Troubleshooting table (`stuck in wip-autopilot`, `autopilot-failed with no error`, `PR branch conflicts main`)

## Labels to create

```
gh label create ai-ready --color 0e8a16 --description "Autopilot may attempt this issue"
gh label create needs-info --color fbca04 --description "Autopilot flagged as needing more context"
gh label create wip-autopilot --color 1d76db --description "Autopilot actively working on this issue"
gh label create autopilot-failed --color b60205 --description "Autopilot dispatch failed — manual intervention needed"
gh label create autopilot-skipped --color cccccc --description "Autopilot declined (out of scope)"
gh label create autopilot-pr --color 5319e7 --description "PR was opened by autopilot — watch for review comments"
```

## Verification

```bash
# 1. Dry-run on existing issue #1
python3 scripts/autopilot/classify_and_dispatch.py --dry-run --issue 1
# Expected: classifier decides OUT_OF_SCOPE (critical bug + requires git recovery judgment)

# 2. Create test issue with acceptance criteria
gh issue create --title "Add X to Y page" \
    --body "Acceptance: X field shown on /dashboard. File: frontend/src/pages/Dashboard.jsx. Test: assert field visible in SupportPage test." \
    --label ai-ready

# 3. Run dispatcher manually
gh workflow run autopilot-issue-loop.yml

# 4. Watch the run
gh run list --workflow autopilot-issue-loop.yml --limit 3
gh run view <run-id> --log

# 5. If PR created, review diff manually, merge or close
```

## Rollout plan

1. **Phase 0: Label hygiene.** Create the 6 labels. Back-label existing issue #1 appropriately.
2. **Phase 1: Classifier only, no dispatch.** Ship the Haiku classifier + `needs-info` / `autopilot-skipped` behavior. Run for 1 week. Verify the classifier's judgment matches Aidan's on every issue before letting it write code.
3. **Phase 2: Dispatch with confirmation gate.** Add dispatch, but require Aidan to comment `autopilot: go` on a `wip-autopilot` issue before Codex actually runs. Eliminates runaway loops during calibration.
4. **Phase 3: Full autopilot.** Remove the confirmation gate. Monitor cost via managed-agents spend tracker. Pause if cost/tick exceeds $3.
5. **Phase 4: PR comment handler.** Ship the review-comment workflow. Start with manual smoke test on 2-3 real review cycles before trusting it.

## Out of scope

- Mouse-wiggler / Teams inactivity defeater (solo founder, irrelevant)
- Slack webhook notifications (email to `help@agentnexlify.com` is enough for Phase 1)
- Multi-repo support (agentnexlify-only)
- Auto-merge (never)
- Automatic label creation on `gh issue create` (labels set manually or via issue template)
- Replacing the existing `build-loop` skill (complementary — issue-driven vs backlog-driven)
- LLM Council invocations from inside autopilot (council is for human decisions, not code gen)

## Risks + mitigations

1. **Runaway cost loop:** classifier + dispatcher + PR comment handler all hit Anthropic API. Worst case: infinite PR ↔ comment cycle. **Mitigation:** hard per-PR comment limit (max 5 autopilot commits per PR before requiring human merge or close). Global monthly cost cap set via `MANAGED_AGENTS_MONTHLY_BUDGET` env var on the runner.
2. **Pre-commit hook false positives:** autopilot commit blocked by hook, issue stuck in `wip-autopilot`. **Mitigation:** dispatcher retries once, then posts failure + `autopilot-failed` + removes `wip-autopilot`. Aidan sees it in issue list.
3. **Bad classifier judgment:** Haiku marks a security issue as READY. Dispatcher modifies auth code. **Mitigation:** classifier prompt explicitly lists "security, billing, customer comms, legal" as OUT_OF_SCOPE. Phase 2 gate (manual "go" comment) catches this during calibration.
4. **Branch name collisions:** two ticks race on the same issue. **Mitigation:** `concurrency: group: autopilot-issue-loop` at workflow level + `wip-autopilot` label as mutex.
5. **Bot token leak:** `AUTOPILOT_GH_TOKEN` in repo secrets. If leaked, attacker can open PRs as the bot. **Mitigation:** fine-grained PAT with only `contents:write`, `issues:write`, `pull_requests:write` on this single repo. Rotate quarterly.
6. **Autopilot opens PR that breaks production:** pre-commit passes, pre-push build passes, but runtime breaks. **Mitigation:** Aidan reviews every PR manually before merge. Never auto-merge. Staging deploy via Vercel preview env on every PR — check preview before merging.
7. **Hash collision in marker comment:** idempotency breaks, duplicate comments spam the issue. **Mitigation:** use SHA-256 of `issue.body + sorted(comment.body for comment in comments)`, not a truncated hash.
8. **Codex infra drift:** `codex exec` flag semantics change between versions. **Mitigation:** pin Codex CLI version in workflow file. Document in skill Gotchas.

## Cost model

- **Classifier:** Haiku, ~500 input + 200 output tokens per tick. Call fires only if ready issues exist. ~$0.0008/call. Budget ≤ $0.003/tick even if 3 issues classified.
- **Dispatcher:** Sonnet via Codex, ~20-50k tokens per dispatch. ~$0.30-0.75/dispatch. Capped at 1 dispatch/tick = max ~$72/month if every tick dispatches. Realistic: 5-10 dispatches/week = ~$15/month.
- **PR comment handler:** Sonnet, ~5-15k tokens per comment. ~$0.08-0.20 each. 20 comments/week = ~$15/month.
- **Total ceiling:** ~$30-100/month depending on volume. Well below the current Anthropic usage for production traffic.

## Critical file reference

| File | Purpose | Status |
|---|---|---|
| `.github/workflows/autopilot-issue-loop.yml` | 15-min cron | NEW |
| `.github/workflows/autopilot-pr-review.yml` | Review comment handler | NEW |
| `scripts/autopilot/classify_and_dispatch.py` | Classifier + dispatcher | NEW |
| `scripts/autopilot/implement_review_comment.py` | PR comment handler | NEW |
| `scripts/autopilot/README.md` | Operator doc | NEW |
| `.claude/skills/autopilot-loop/SKILL.md` | Claude wrapper skill | NEW |
| `.claude/skills/build-loop/SKILL.md` | Existing backlog loop — unchanged, complementary | EXISTING |
| `.claude/skills/worktree-orchestrator/SKILL.md` | Worktree dispatch pattern — unchanged, reused | EXISTING |
| `scripts/hooks/pre-commit` | Secret + __future__ + bare-except guards — unchanged, gates autopilot commits | EXISTING |

## Delegation model

Per `.claude/rules/model-routing.md`: **Opus plans** (this doc). **Sonnet executes** the implementation in a dedicated session, phase-by-phase:

- Session 1: Phase 0 + 1 (labels + classifier only, no dispatch)
- Session 2: Phase 2 + 3 (dispatcher + manual-gate removal)
- Session 3: Phase 4 (PR comment handler)

Each session runs tests between phases. Pre-push gates enforce widget sync + build cleanliness. No single session tries to ship all 4 phases.
