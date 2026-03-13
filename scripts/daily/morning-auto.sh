#!/usr/bin/env bash
# AgentNexLiFy Automated Morning Routine
# Runs claude -p headlessly to perform intelligent morning startup
# Scheduled via Task Scheduler (Windows) or cron (Linux/macOS)

set -e

# Configuration
REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_DIR="$REPO_DIR/docs/daily-logs"
DATE=$(date -u '+%Y-%m-%d')
LOG_FILE="$LOG_DIR/auto-morning-$DATE.log"

cd "$REPO_DIR"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

echo "[$(date)] Starting automated morning routine..." >> "$LOG_FILE"

# Ensure we're on the latest code
git pull --rebase 2>> "$LOG_FILE" || echo "Git pull failed, continuing with local state" >> "$LOG_FILE"

# Run Claude Code headlessly with restricted permissions
claude -p "
You are running the automated morning routine for AgentNexLiFy. You are in headless mode — there is no human to interact with. Work autonomously.

## Your Context
- Read CLAUDE.md for full repo context
- Read docs/dev-knowledge/bug-patterns.md for known issues
- Read docs/dev-knowledge/schema-log.md for schema state
- Read docs/dev-knowledge/architecture-decisions.md for design context
- Read docs/daily-logs/current-tasks.md for the existing task backlog (create it if it doesn't exist)

## Step 1: Health Check
Run these checks and record the results:
1. Scan backend/routers/ files for 'from __future__ import annotations' (CRITICAL if found)
2. Count bare except blocks in backend Python files
3. Check .env is in .gitignore
4. Check for hardcoded API keys/tokens in code files (sk_live_, sk_test_, sk-ant-)
5. Scan for TODO/FIXME comments in backend/ and frontend/src/ and count them
6. Check widget file sync (widget/ vs frontend/public/widget/)

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

echo "[$(date)] Morning routine completed." >> "$LOG_FILE"
