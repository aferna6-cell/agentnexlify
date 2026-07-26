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

9G. **KB autopopulate self-healing trigger** (added run 102, 2026-07-25):
    Condition: `DAYS_STALE` from Step 9F is already computed. Fire when `DAYS_STALE -gt 7`.
    If Step 9F was skipped (log format unreadable or file missing), skip Step 9G.
    1. **Trigger kb-autopopulate.yml:**
       ```bash
       gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify
       GH_EXIT=$?
       ```
    2. **If gh workflow run exits non-zero** (permission error, spending limit, token expired):
       Add comment via `mcp__github__add_issue_comment`:
         issue_number: 403
         body: "**Step 9G: kb-autopopulate.yml trigger FAILED** (exit code: $GH_EXIT). Possible causes: (1) GH Actions spending limit hit — check GH #500. (2) AUTOPILOT_GH_TOKEN expired — check GH #399. (3) Workflow dispatch not enabled on branch."
       Log: "Step 9G: workflow trigger FAILED (exit $GH_EXIT) — comment added to GH #403"
       Skip to step 10.
    3. **Wait for job to queue:**
       `sleep 30`
    4. **Check run status:**
       ```bash
       RUN_JSON=$(gh run list --workflow=kb-autopopulate.yml --limit=1 --json conclusion,createdAt,url 2>/dev/null)
       CONCLUSION=$(echo "$RUN_JSON" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r[0].get('conclusion','') if r else '')" 2>/dev/null || echo "")
       RUN_URL=$(echo "$RUN_JSON" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r[0].get('url','') if r else '')" 2>/dev/null || echo "")
       ```
    5. **Branch on conclusion:**
       - If `CONCLUSION == "success"`: log "Step 9G: kb-autopopulate triggered — SUCCESS ($RUN_URL)" and continue to step 10.
       - If `CONCLUSION == "failure"` or `"cancelled"`:
         Add comment via `mcp__github__add_issue_comment`:
           issue_number: 403
           body: "**Step 9G: kb-autopopulate.yml triggered but FAILED.** Check: (1) ANTHROPIC_API_KEY in GH Actions Secrets. (2) VOYAGE_API_KEY in GH Actions Secrets. (3) SUPABASE_ACCESS_TOKEN. (4) GH Actions spending limit — check GH #500. Run URL: $RUN_URL"
         Log: "Step 9G: kb-autopopulate FAILED — diagnostic comment added to GH #403 ($RUN_URL)"
       - If `CONCLUSION` still empty (run in progress after 30s):
         Log: "Step 9G: kb-autopopulate running — status pending ($RUN_URL)"
         Continue to step 10 (CI completes on its own).

9H. **GH Actions spending-limit daily heartbeat** (added run 104, 2026-07-26-pm):
    Condition: Unconditional — runs every nightly cycle.
    1. **Query recent run conclusions:**
       ```bash
       FAIL_COUNT=$(gh run list --limit=5 -R aferna6-cell/agentnexlify \
         --json conclusion 2>/dev/null | \
         python3 -c "import json,sys; r=json.load(sys.stdin); print(sum(1 for x in r if x.get('conclusion')=='failure'))" \
         2>/dev/null || echo "0")
       ```
       Log: "Step 9H: {FAIL_COUNT}/5 recent Actions runs failed"
    2. **If FAIL_COUNT >= 4** (spending-limit outage pattern):
       a. Check GH #500 state:
          ```bash
          GH500_STATE=$(gh issue view 500 -R aferna6-cell/agentnexlify \
            --json state -q .state 2>/dev/null || echo "unknown")
          ```
       b. If state == "open": Add comment via `mcp__github__add_issue_comment`:
            issue_number: 500
            body: "**Step 9H nightly heartbeat:** GH Actions still down as of {TODAY} ({FAIL_COUNT}/5 recent runs failed). Day {N} since 2026-07-20. Fix: github.com/settings/billing/summary → raise spending limit. If resolved, please close this issue to silence this alert."
          Log: "Step 9H: Actions down (day {N}) — daily ping added to GH #500"
       c. If state == "closed": Log "Step 9H: GH #500 closed — Actions restored. Heartbeat complete."
    3. **If FAIL_COUNT < 4:** Log "Step 9H: GH Actions healthy ({FAIL_COUNT}/5 failed)"

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
