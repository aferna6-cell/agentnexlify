#!/usr/bin/env bash
# AgentNexLiFy Automated Morning Routine
# Runs claude -p headlessly to perform intelligent morning startup
# Scheduled via Task Scheduler (Windows) or cron (Linux/macOS)

set -euo pipefail

# Configuration
REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
COMMON_SH="$REPO_DIR/scripts/daily/common.sh"
# shellcheck source=./common.sh
source "$COMMON_SH"
LOG_DIR="$REPO_DIR/docs/daily-logs"
DATE="$(daily_date)"
LOG_FILE="$LOG_DIR/auto-morning-$DATE.log"

cd "$REPO_DIR"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

log_line "$LOG_FILE" "Starting automated morning routine..."
trap 'exit_code=$?; log_exit_status "$LOG_FILE" "Automated morning routine" "$exit_code"' EXIT

# Ensure we're on the latest code when safe
git_pull_if_clean "$LOG_FILE"

# Capture a static health snapshot even if the headless agent fails to start
log_line "$LOG_FILE" "Static health snapshot:"
bash "$REPO_DIR/scripts/daily/health-check.sh" >> "$LOG_FILE" 2>&1 || log_line "$LOG_FILE" "Static health snapshot failed."

CLAUDE_BIN="$(ensure_claude_bin "$LOG_FILE")"
log_line "$LOG_FILE" "Using Claude CLI: $CLAUDE_BIN"

# Run Claude Code headlessly
"$CLAUDE_BIN" -p "
You are running the automated morning routine for AgentNexLiFy. You are in headless mode — there is no human to interact with. Work autonomously.

## Your Context
- Read CLAUDE.md for full repo context
- Read docs/dev-knowledge/bug-patterns.md for known issues
- Read docs/dev-knowledge/schema-log.md for schema state
- Read docs/dev-knowledge/architecture-decisions.md for design context
- Read docs/daily-logs/current-tasks.md for the existing task backlog (create it if it doesn't exist)

## Step 1: Health Check
Run these checks and record the results:
1. Run `bash scripts/daily/health-check.sh` and capture its results first (dangerous router imports, bare except count, silent frontend catch count, widget sync, .env gitignore status)
2. Check for hardcoded API keys/tokens in code files (sk_live_, sk_test_, sk-ant-)
3. Scan for TODO/FIXME comments in backend/ and frontend/src/ and count them

## Step 2: Recent Activity Analysis
1. Check git log for last 24 hours — what was committed?
2. Check if any bug fix commits exist that aren't documented in docs/dev-knowledge/bug-patterns.md
3. Check if any migration files were added that aren't in docs/dev-knowledge/schema-log.md
4. Look at the most frequently modified files in the last 7 days

## Step 3: Generate Task List
Based on your analysis, generate a prioritized task list:
- Priority 1: Critical health issues (build failures, security problems, dangerous imports)
- Priority 2: Documentation gaps (undocumented bug fixes, missing schema log entries)
- Priority 3: Code quality (bare excepts to fix, TODOs to address)
- Priority 4: Improvements (refactoring opportunities, new skill suggestions)

Carry forward unfinished tasks from docs/daily-logs/current-tasks.md if it exists.

## Step 4: Execute Safe Tasks
Autonomously execute tasks that are SAFE to do without human review:
- Update docs/dev-knowledge/schema-log.md with any undocumented migrations
- Update docs/dev-knowledge/bug-patterns.md with any undocumented fix commits (add skeleton entries)
- Update docs/daily-logs/current-tasks.md with the new prioritized task list

Do NOT:
- Modify any API endpoints or routes
- Change any database queries or Pydantic models
- Modify the frontend application code
- Touch .env files or anything with secrets
- Create or run database migrations
- Modify CLAUDE.md (only update knowledge base files in docs/)

## Step 5: Write Daily Log
Create docs/daily-logs/$DATE.md with:
- Morning health check results
- Tasks identified and prioritized
- Tasks auto-completed
- Tasks requiring human attention
- Recommended agent delegation for remaining tasks (reference the agents: schema-guardian, backend-dev, frontend-dev, widget-specialist, qa-tester, devops)

## Step 6: Commit
Stage and commit your changes with:
git add docs/
git commit -m 'docs: automated morning startup $DATE'

Do NOT push — the developer will push when ready.

Be thorough but stay within your safety boundaries. Write everything to files, not stdout.
" \
  --dangerously-skip-permissions \
  >> "$LOG_FILE" 2>&1
