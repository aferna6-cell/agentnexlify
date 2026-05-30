---
name: nightly-commit-review
description: Nightly autonomous review of last 24h commits. Haiku triages, Sonnet fixes low-risk bugs only, commits + pushes to main. Medium/high risk → GH issue instead. Runs at 2:37 AM local via scheduled-tasks MCP. Use when user says "nightly review", "review last night's commits", or manual trigger.
version: 1.0.0
origin: agentnexlify
user-invocable: true
disable-model-invocation: true
allowed-tools: [Bash, Read, Write, Edit, Grep, Glob]
effort: high
triggers:
  - nightly review
  - review last night's commits
  - run nightly
  - bug hunt last 24h
  - autonomous review
---

# Nightly Commit Review — Autonomous Bug Finder

Runs unattended overnight. Finds bugs in last 24h of commits. Fixes the safe ones. Files issues for the risky ones.

## When to Use
- Scheduled firing at 2:37 AM local via `nightly-commit-review` task
- Manual catch-up after a missed night: `bash scripts/daily/nightly-commit-review.sh`
- After a big merge when you want a separate eyes-on review
- Pre-deploy sanity sweep on recent commits

## When NOT to Use
- During active feature work (runs against your uncommitted state — noisy)
- When working tree is dirty (script aborts anyway)
- For medium/high-risk changes (it files issues, doesn't fix — use `/fix-bug` directly)
- Inside FORBIDDEN paths (migrations, auth, stripe, widget — skill refuses)

## Trigger
- Scheduled: `37 2 * * *` local (daily 2:37 AM) via `mcp__scheduled-tasks__create_scheduled_task`
- Manual: `bash scripts/daily/nightly-commit-review.sh`
- Task ID: `nightly-commit-review`

## Model Routing (strict)
| Phase | Model | Why |
|-------|-------|-----|
| Triage (scan diff, classify findings) | **Haiku** | cheap, high throughput on mechanical scan |
| Fix (low-risk only) | **Sonnet** | needs real judgment on code |
| Review own fix | **Haiku** | second-pass verification |
| Medium/high risk → open GH issue | **Haiku** | templated output |

## Scope — WHAT to review
```bash
git log --since="1 day ago" --oneline
git diff "HEAD@{1 day ago}"..HEAD
```
Only commits in last 24h. Skip merge commits.

## Risk Classification

### LOW — Autonomous fix allowed (commit + push to main)
- Typos in comments, docstrings, docs
- Dead code removal (zero-reference functions/imports)
- Unused imports
- Missing null/undefined checks in non-critical paths
- Linter warnings (formatting, unused vars)
- Missing error context in log messages
- Obvious off-by-one in test assertions (NOT in production logic)
- Doc inconsistencies with code
- **New `.claude/skills/*/SKILL.md` creation** when the most recent `subconscious/runs/*/winning-concept.md` contains the text `AUTONOMOUS-EXECUTABLE` and the winning concept describes creating a skill file. Execute directly — do not classify as "docs only" and skip.

### MEDIUM — Open GH issue, DO NOT fix autonomously
- Logic bugs in production code paths
- Missing tests for new behavior
- Unhandled error cases
- Race conditions
- Performance regressions (N+1 queries, unbounded loops)
- Type coercion bugs

### HIGH — Open GH issue with P0 label, page user
- Auth bypass paths
- Tenant isolation leaks (`client_id` missing from query)
- Secret leakage in logs/responses
- Stripe webhook sig bypass
- Schema drift (code references column that doesn't exist)
- Broken migrations
- XSS/SQLi/CSRF vectors
- Dependencies with CVEs

### FORBIDDEN — Never touch autonomously
- `migrations/*.sql`
- `backend/routers/auth.py`, `backend/routers/stripe_webhooks.py`, `backend/routers/billing.py`
- `backend/dependencies.py`
- `.env*`, secrets, any credential-adjacent file
- Widget files (`widget/agentnexlify-widget.js`, `frontend/public/widget/agentnexlify-widget.js`) — byte-identical sync invariant
- `CLAUDE.md`, `AGENTS.md`
- Anything in `_archive/`, `landing-page-v2/`

## Guardrails
1. **Max 5 files per run** — more = bail out, file issue instead
2. **Max 50 LOC changed per run** — larger = bail
3. **Must run `npm run agent-system:check`** before push — if it fails, abort
4. **Must not modify tests to make them pass** — Rule 10 (user-rules.md)
5. **Must run existing pre-push hook** (doesn't skip with `--no-verify`)
6. **One commit per fix** — not batched
7. **Commit message format:** `fix(nightly): <one-line> [auto-nightly-YYYY-MM-DD]`

## Output Artifacts
Every run writes a report:
```
docs/dev-knowledge/nightly-reviews/YYYY-MM-DD.md
```

Report structure:
```markdown
# Nightly Review — YYYY-MM-DD

## Commits reviewed
- abc1234 fix(foo): ...
- def5678 feat(bar): ...

## Findings
### Fixed autonomously (N)
- [LOW] typo in README.md:42 → commit xyz9876

### Issues opened (N)
- [MEDIUM] #123 — potential N+1 in routers/leads.py:87
- [HIGH] #124 — missing client_id in conversations query

### Skipped
- commits touching FORBIDDEN paths (N)

## Next action
[one-liner: all clear | N issues need human | BLOCKED by HIGH]
```

## Moratorium Escalation Protocol

After writing the nightly report, check governance state:

1. Read `subconscious/state/governance.json`
2. If `moratorium_config.moratorium_active == true`:
   a. Count `active_directions` where `status == "pending_approval"` → N_pending
   b. Find oldest pending item (earliest `date` field) → compute days since `date` → oldest_age_days
   c. If N_pending > 3 AND oldest_age_days > 14:
      - Load GitHub MCP tools via ToolSearch (mcp__github__search_issues, mcp__github__add_issue_comment, mcp__github__issue_write)
      - Search open GH issues: label `moratorium` + state=open
      - None found: create issue via `mcp__github__issue_write` (title/body per template below)
      - Found: add comment via `mcp__github__add_issue_comment` with current pending count + ages
   d. Log action in report under `## Moratorium Status`
3. If `moratorium_active == false`: skip, log "moratorium inactive — no escalation needed"

### Moratorium Issue Template
**Title:** `[subconscious] Moratorium active: {N} pending items, oldest {X} days`
**Labels:** `subconscious`, `moratorium`
**Body:**
```
## AgentNexLiFy Subconscious — Moratorium Alert

Moratorium active for {X} days. {N} pending recommendations blocking new autonomous work.

| Run | Title | Days pending | Status |
|-----|-------|--------------|--------|
{rows from active_directions where status=pending_approval}

**Fastest path to exit:** invoke `/moratorium-sprint` in any interactive session (~50 min, opens draft PR).
Latest sketch: `subconscious/runs/{winning-run-date}/winning-concept.md`

Auto-generated by nightly-commit-review on {DATE}.
```

Escalation frequency: once per nightly run only. If today's run already commented, skip.
No-op when moratorium is inactive.

## Scheduled Task Prompt
```
You are the AgentNexLiFy nightly commit reviewer. It is 2:37 AM local, time to review.

1. cd /home/aidan/agentnexlify
2. git pull origin main --rebase
3. Run: git log --since="1 day ago" --oneline --no-merges
4. If zero commits: write empty report, exit.
5. For each commit: git show <hash>
6. Classify every finding per .claude/skills/nightly-commit-review/SKILL.md risk tiers
7. For LOW findings: Use Sonnet to fix, one commit per fix, push
8. For MEDIUM/HIGH: Use Haiku to draft GH issue body, open via `gh issue create --label ai-nightly,ai-ready`
9. Write report to docs/dev-knowledge/nightly-reviews/YYYY-MM-DD.md
9A. (Moratorium Escalation) Read `subconscious/state/governance.json`.
    If moratorium_config.moratorium_active == true:
      a. Count pending_approval items in active_directions → N_pending
      b. Find oldest pending item (earliest date field), compute days since → oldest_age
      c. If N_pending > 3 AND oldest_age > 14:
         - Load mcp__github__ tools via ToolSearch
         - Search GH issues: label=moratorium + state=open
         - None found: create issue via mcp__github__issue_write (per Moratorium Issue Template)
         - Found: add comment via mcp__github__add_issue_comment (pending count + ages)
      d. Add "## Moratorium Status" to report
10. Commit report: `docs(nightly): review YYYY-MM-DD [auto-nightly]`
11. Push to main
12. If any guardrail tripped (forbidden path, >5 files, >50 LOC, test-check failed) — abort fixes, file issue only, still write report
```

## Integration with existing infra
- Feeds issues to `issue-to-pr-loop` skill (already polls GH every 15 min)
- Report directory `docs/dev-knowledge/nightly-reviews/` is git-tracked (audit trail)
- Pre-push hook still gates every push (code quality review, schema check)
- Uses existing `code-reviewer` agent patterns

## Disable
```bash
# List
mcp__scheduled-tasks__list_scheduled_tasks

# Disable (keeps task, stops firing)
mcp__scheduled-tasks__update_scheduled_task taskId=nightly-commit-review enabled=false

# Or set CLAUDE_NIGHTLY_REVIEW=0 in env → script no-ops
```

## Failure modes
- Machine off / Claude Code closed → task doesn't fire (scheduled-tasks MCP limitation). Missed nights logged in GH issue on next run.
- Push rejected (main moved) → rebase, retry once, else abort with report flag.
- Tests fail after fix → revert commit, file issue.
- gh CLI unauthenticated → skip issue creation, write findings to report only.

## Cross-refs
- `.claude/rules/user-rules.md` — Rule 10 (don't change tests), Rule 7 (honor CLAUDE.md)
- `.claude/rules/model-routing.md` — Haiku/Sonnet/Opus boundaries
- `docs/dev-knowledge/bug-patterns.md` — known-bad patterns to flag
- `scripts/daily/nightly-commit-review.sh` — manual trigger
