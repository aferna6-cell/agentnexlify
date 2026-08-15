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
- **Bash additions to `scripts/hooks/pre-commit`** when `subconscious/state/governance.json` has a matching `active_directions[]` entry where `"autonomous_executable": true` and the most recent `subconscious/runs/*/winning-concept.md` contains `AUTONOMOUS-EXECUTABLE`. Execute the patch in the winning concept directly — commit to main as `ci(pre-commit): <description from winning concept>`. **Pre-condition required**: run the script being wired first — if it exits non-zero, the item is blocked; log the blocker and open a MEDIUM issue instead of wiring.
- **New `.github/workflows/*.yml` files** when the most recent `subconscious/runs/*/winning-concept.md` has `AUTONOMOUS-EXECUTABLE` label AND provides the inline file content verbatim. Apply the inline content exactly as written. Commit as `ci(eval): add <filename> [auto-nightly-YYYY-MM-DD]`. After commit: update `governance.json` matching `active_directions` entry status → `implemented`.

  **Current pending item (Item A):** Wire `check_project_invariants.py` as pre-commit Check 10. Status: `pending_autonomous`. Blocked 2026-06-01: script fails on em-dash violations in UI copy. Execute when script passes clean.

  Patch (add before `exit 0` at end of `scripts/hooks/pre-commit`):
  ```bash
  # Check 10 — project invariants (client_id, status, areas_of_interest)
  if command -v python3 &>/dev/null; then
    python3 scripts/check_project_invariants.py || { echo "❌ Pre-commit: check_project_invariants.py failed"; exit 1; }
  fi
  ```
  Commit: `ci(pre-commit): wire check_project_invariants.py as Check 10`
  After commit: update `governance.json` active_directions Item A status → `implemented`.

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
8. **Detached HEAD guard (CRITICAL)** — before any commit, verify on a branch. Commits on detached HEAD are orphaned and never reach main. Run: `BRANCH=$(git symbolic-ref HEAD 2>/dev/null); if [ -z "$BRANCH" ]; then git checkout main && git pull origin main; fi`. Verify after: `git symbolic-ref HEAD` must output `refs/heads/main`.

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
1.5. **Detached HEAD guard:** `BRANCH=$(git symbolic-ref HEAD 2>/dev/null); if [ -z "$BRANCH" ]; then git checkout main && git pull origin main; fi`
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
9B. (Healthz Monitor Maintenance) Check if `ops/monitoring/healthz-alert.sh` exists:
    ```bash
    ls ops/monitoring/healthz-alert.sh 2>/dev/null || echo "MISSING"
    ```
    If MISSING: write the file from the embedded content in the latest
    `subconscious/runs/*/winning-concept.md` that contains "## Script Content".
    Commit: `ops(monitoring): add healthz-alert.sh [auto-nightly-YYYY-MM-DD]`
    Also check if `ops/monitoring/SETUP.md` exists; write it if missing.
    After both files created: open GH issue "Set SLACK_ALERT_WEBHOOK_URL in Railway"
    with label `human-action-required` and body from subconscious/runs/2026-07-03/winning-concept.md §Human Step.
    If ALREADY EXISTS: log "healthz-alert.sh present — monitoring active" and skip.
9C. (Brain Connector Health Check) Read last 20 lines of `brain/INGESTION-LOG.md`:
    ```bash
    tail -20 brain/INGESTION-LOG.md
    ```
    Count consecutive entries ending with `error —` or `skipped —` (from bottom up, stop on first
    success or gap). If consecutive_failures >= 3:
      a. Search for existing open GH issue with label `brain-connector-failure`:
         Use mcp__github__search_issues with query "repo:aferna6-cell/agentnexlify label:brain-connector-failure state:open"
      b. If NO labeled issue found — also search for open issues mentioning brain connector
         (query: "repo:aferna6-cell/agentnexlify brain connector state:open").
         If related open issues exist: add comment to the most recent human-action-required
         issue with updated failure count and days-since-last-success. Log:
         "brain connector failure escalated via comment on #N — skipping duplicate issue"
         If no related issues exist at all: create GH issue via mcp__github__issue_write:
           title: "Brain connector failing N consecutive days — credentials need rotation"
           labels: ["human-action-required", "brain-connector-failure", "operational", "critical"]
           body: document failure count, errors from INGESTION-LOG, fix steps (rotate GitHub PAT
           + set SUPABASE_ACCESS_TOKEN in Railway), reference brain/_tools/refresh_connectors.py
      c. If labeled issue FOUND: log "brain connector failure already escalated (issue #N open) — skipping duplicate"
    If consecutive_failures < 3:
      Log: "brain connector check PASS — last entry shows success or < 3 consecutive failures"
    ### Step 9C age gate (brain connector staleness)
    After the consecutive-failures check, also check age of last successful entry:
    1. Parse timestamp of last successful INGESTION-LOG.md entry (format: `YYYY-MM-DDTHH:MMZ`)
    2. Compute days_since_last_run = today - last_success_date
    3. If days_since_last_run > 14:
       - Surface as WARNING in nightly summary: "Brain connector {N} days since last run (threshold: 14 days). Last run: {date}."
       - Check if #394 or #399 are open (search: "repo:aferna6-cell/agentnexlify brain connector credentials state:open")
       - If open issue exists: add comment with current staleness count + last-run date. Log: "brain connector staleness escalated via comment on #N"
       - If no existing open issue: create via mcp__github__issue_write: title "Brain connector {N} days stale — last run {date}", labels: ["human-action-required", "brain-connector", "operational"]
    4. If days_since_last_run <= 14: PASS (age gate OK)
9D. (Issue-to-PR Loop Health Check) Check for stalled ai-ready issues and loop health:
    1. **Check for stalled ai-ready issues:**
       List open ai-ready issues: `mcp__github__list_issues` with `labels: ["ai-ready"], state: OPEN`
       For each open ai-ready issue, search for linked PR:
         `mcp__github__search_pull_requests` query: `repo:aferna6-cell/agentnexlify is:pr <issue_number>`
       Flag any ai-ready issue that has been open >24h with no linked PR as stalled.
    2. **Check loop execution health:**
       List recent runs: `mcp__github__actions_list` method=list_workflow_runs,
         resource_id=autopilot-issue-loop.yml, per_page=5
       If last successful run > 4h ago OR all 5 recent runs = failure → flag as dormant/erroring.
    3. **If stalled issue + loop failure found:**
       a. Add comment to the stalled GH issue via `mcp__github__add_issue_comment`:
          "Step 9D health check: ai-ready issue open >24h with no linked PR.
           Loop last ran: {timestamp}. Loop status: STALLED — {N} consecutive failures.
           Possible causes: AUTOPILOT_GH_TOKEN expired, workflow disabled, ANTHROPIC_API_KEY missing."
       b. Search for existing open issue about loop dormancy:
          `mcp__github__search_issues` query: "repo:aferna6-cell/agentnexlify autopilot-issue-loop state:open"
          If NONE found: create GH issue via `mcp__github__issue_write`:
            title: "autopilot-issue-loop GitHub Actions failing N days — <likely cause> [CRITICAL]"
            labels: ["human-action-required", "nightly-review", "operational"]
            body: consecutive failure count, first/last failure timestamps, failing step,
                  likely root cause, fix steps (rotate AUTOPILOT_GH_TOKEN), affected ai-ready issues
          If FOUND: add comment with updated failure count + latest failure timestamp
    4. **If no stalled issues and loop healthy:**
       Log: "Step 9D PASS — {N} ai-ready issues, all have linked PRs or <24h old, loop ran {timestamp}"
    Log result: "Step 9D: {N} ai-ready issues, {M} stalled, loop last ran {timestamp}, status: {PASS|STALLED}"
9E. (Proactive Credential Rotation Tracking) Check credential rotation schedule for approaching expiries:
    1. **Check if schedule file exists:**
       ```bash
       ls ops/credential-rotation-schedule.md 2>/dev/null || echo "MISSING"
       ```
       If MISSING: log "Step 9E: ops/credential-rotation-schedule.md not found — skipping" and continue to step 10.
    2. **Read schedule and compute days since last rotation:**
       Read `ops/credential-rotation-schedule.md` line by line.
       For each credential row: parse "Last rotated" date field.
       Compute days_since_rotation = (today - last_rotated_date).
       Flag as approaching_expiry if days_since_rotation >= 76 (= 90 days - 14-day warning window).
       If last_rotated is "unknown" or "not yet set": flag as unknown_state, log separately.
    3. **If any credential approaching expiry (days_since_rotation >= 76):**
       a. Search open GH issues with label `credential-rotation`:
          `mcp__github__list_issues` with labels: ["credential-rotation"], state: OPEN
       b. If NO open credential-rotation issue exists:
          Create GH issue via `mcp__github__issue_write`:
            title: "Credential rotation due in ≤14 days: [credential name(s)]"
            body: credential name, last_rotated date, days_since_rotation, expected expiry, rotation steps
            labels: ["credential-rotation", "human-action-required"]
       c. If open credential-rotation issue FOUND:
          Add comment via `mcp__github__add_issue_comment` with updated days_since_rotation.
    4. **Log result:**
       Add to nightly commit log: "Step 9E: {N} credentials checked, {M} approaching expiry (>=76 days), {K} unknown state"
9F. (KB Autopopulate Staleness Check) Check when knowledge base was last successfully populated:
    1. **Read KB log:**
       Read `knowledge-base/log.md`.
       If file missing: log "Step 9F: knowledge-base/log.md not found — skipping" and continue to step 10.
    2. **Extract last run date:**
       Find the most recent `## [YYYY-MM-DD` header in the file (format: `## [2026-07-13 20:00]`).
       Parse date as YYYY-MM-DD.
       If no date found: log "Step 9F: KB log format unreadable — skipping" and continue to step 10.
    3. **Compute days stale:**
       days_stale = (today - last_run_date) in days.
       Log: "Step 9F: KB autopopulate last run: {last_run_date} ({days_stale} days ago)"
    4. **If days_stale > 7:**
       a. Add comment via `mcp__github__add_issue_comment`:
          issue_number: 403
          body: "**KB autopopulate staleness alert (Step 9F):** {days_stale} days since last successful run (last: {last_run_date}). Check: (1) ANTHROPIC_API_KEY in GitHub Actions secrets — may need rotation. (2) SUPABASE_ACCESS_TOKEN — may be expired. Manual trigger: `bash scripts/daily/kb-autopopulate.sh`."
       b. If GH comment fails (token expired — GH #399): log "Step 9F: GH comment failed — KB stale {days_stale} days, token may be expired" and continue.
       c. Log: "Step 9F: KB STALE ({days_stale} days) — comment added to GH #403"
9G. (KB Autopopulate Self-Healing) When Step 9F flags staleness > 7 days, trigger the autopopulate workflow:
    1. **Reuse Step 9F staleness signal:**
       If days_stale <= 7: skip this step entirely (Step 9F already logged clean state).
       If days_stale > 7: proceed.
    2. **Trigger workflow:**
       Run: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`
       If command fails (exit non-zero): log "Step 9G: gh workflow run failed — check GH token or workflow name" and continue to step 10.
    3. **Wait for initial status:**
       `sleep 30`
       Run: `gh run list --workflow=kb-autopopulate.yml -R aferna6-cell/agentnexlify --limit=1 --json conclusion,url`
       Parse `conclusion` and `url` from JSON output.
    4. **Report outcome:**
       a. If conclusion == "success":
          Log: "Step 9G: kb-autopopulate triggered — SUCCESS"
       b. If conclusion == "failure" or "cancelled" or "timed_out":
          Add comment via `mcp__github__add_issue_comment`:
            issue_number: 403
            body: "**Step 9G: kb-autopopulate.yml triggered but FAILED.** Check ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN in GitHub Actions Secrets. Run URL: {url}"
          If GH comment fails: log "Step 9G: comment failed — kb-autopopulate run FAILED, check GH #403 manually"
       c. If conclusion == "" or "in_progress" (still running after 30s):
          Log: "Step 9G: kb-autopopulate running — status pending (CI will complete on its own)"
       d. If gh run list fails or returns no output:
          Log: "Step 9G: could not read run status — trigger may have succeeded, check GH Actions manually"
    5. **Log:**
       Log: "Step 9G: kb-autopopulate trigger attempted — conclusion: {conclusion}"
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
