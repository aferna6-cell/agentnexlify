#!/usr/bin/env bash
# AgentNexLiFy Automated Evening Review
# Runs claude -p headlessly to review the day and update knowledge base

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
COMMON_SH="$REPO_DIR/scripts/daily/common.sh"
# shellcheck source=./common.sh
source "$COMMON_SH"
LOG_DIR="$REPO_DIR/docs/daily-logs"
DATE="$(daily_date)"
LOG_FILE="$LOG_DIR/auto-evening-$DATE.log"

cd "$REPO_DIR"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

log_line "$LOG_FILE" "Starting automated evening review..."
trap 'exit_code=$?; log_exit_status "$LOG_FILE" "Automated evening review" "$exit_code"' EXIT

# Get latest changes when safe
git_pull_if_clean "$LOG_FILE"

log_line "$LOG_FILE" "Static health snapshot:"
bash "$REPO_DIR/scripts/daily/health-check.sh" >> "$LOG_FILE" 2>&1 || log_line "$LOG_FILE" "Static health snapshot failed."

CLAUDE_BIN="$(ensure_claude_bin "$LOG_FILE")"
log_line "$LOG_FILE" "Using Claude CLI: $CLAUDE_BIN"

"$CLAUDE_BIN" -p "
You are running the automated evening review for AgentNexLiFy. You are in headless mode — work autonomously.

## Your Context
- Read CLAUDE.md for full repo context
- Read today's morning log if it exists: docs/daily-logs/$DATE.md
- Read docs/daily-logs/current-tasks.md for the task backlog
- Read docs/dev-knowledge/bug-patterns.md
- Read docs/dev-knowledge/schema-log.md
- Read docs/dev-knowledge/architecture-decisions.md

## Step 1: Review Today's Work
1. Run git log --since='$DATE' --oneline to see today's commits
2. Run git log --since='$DATE' --name-only --pretty=format:'' to see files changed, then sort and deduplicate
3. Count the commits and files changed
4. Identify any fix/bug/patch commits

## Step 2: Update Knowledge Base
For each fix-related commit today:
1. Check if it's already documented in docs/dev-knowledge/bug-patterns.md
2. If not, add a skeleton entry with the commit message, date, and files changed
3. Mark it as 'Auto-logged — needs human enrichment for root cause details'

For each migration file created/modified today:
1. Check if it's documented in docs/dev-knowledge/schema-log.md
2. If not, read the migration SQL and add a summary entry

## Step 3: End-of-Day Health Check
Run the same health checks as the morning:
1. Run `bash scripts/daily/health-check.sh` and capture its results first (dangerous router imports, bare except count, silent frontend catch count, widget sync, .env gitignore status)
2. Compare the static health snapshot against the morning log if it exists

## Step 4: Update Task Backlog
Update docs/daily-logs/current-tasks.md:
1. Move completed tasks (compare with morning plan) to a 'Completed (Recent)' section with today's date
2. Carry forward unfinished tasks
3. Add any new tasks identified from today's review
4. Write 'Tomorrow's Top 3 Priorities' at the top based on what's most important

## Step 5: Write Evening Section
Append to today's daily log (docs/daily-logs/$DATE.md) or create it if it doesn't exist:
- Evening review timestamp
- Commits today (count and list)
- Files changed (count and list)
- Knowledge base updates made
- End-of-day health status
- Tomorrow's priorities
- Self-improvement suggestions (did the same files get modified repeatedly? should a new skill be created?)

## Step 6: Commit
git add docs/
git commit -m 'docs: automated evening review $DATE'

Do NOT push.

Be thorough but stay safe. Only modify files in docs/.
" \
  --dangerously-skip-permissions \
  >> "$LOG_FILE" 2>&1
