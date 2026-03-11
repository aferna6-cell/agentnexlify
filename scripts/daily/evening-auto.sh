#!/usr/bin/env bash
# AgentNexLiFy Automated Evening Review
# Runs claude -p headlessly to review the day and update knowledge base

set -e

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_DIR="$REPO_DIR/docs/daily-logs"
DATE=$(date -u '+%Y-%m-%d')
LOG_FILE="$LOG_DIR/auto-evening-$DATE.log"

cd "$REPO_DIR"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

echo "[$(date)] Starting automated evening review..." >> "$LOG_FILE"

# Get latest changes
git pull --rebase 2>> "$LOG_FILE" || echo "Git pull failed, continuing with local state" >> "$LOG_FILE"

claude -p "
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
1. Dangerous imports in backend/routers/ files
2. Bare except block count (compare with morning if log exists)
3. Widget file sync check
4. .env in .gitignore

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
  --allowedTools "Read,Glob,Grep,Bash(git log*),Bash(git add*),Bash(git commit*),Bash(git pull*),Bash(git diff*),Bash(git status*),Bash(grep*),Bash(find*),Bash(wc*),Bash(cat*),Bash(ls*),Bash(head*),Bash(tail*),Bash(sort*),Bash(date*),Bash(echo*),Bash(mkdir*),Bash(diff*),Write,Edit" \
  --disallowedTools "Bash(rm *),Bash(sudo *),Bash(curl *),Bash(wget *),Bash(pip *),Bash(python *),Bash(node *)" \
  >> "$LOG_FILE" 2>&1

echo "[$(date)] Evening review completed." >> "$LOG_FILE"
