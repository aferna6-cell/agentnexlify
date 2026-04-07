#!/usr/bin/env bash
# Challenge Assumptions — Daily Cron
# Schedule: daily at 9 PM (after evening routine at 8 PM)
# Reads wiki articles updated in the last 7 days and generates steelman
# counterarguments, alternative explanations, and blind spots for each.
#
# To add to cron: 0 21 * * * /home/aidan/agentnexlify/scripts/daily/challenge-assumptions.sh
# To add to Windows Task Scheduler: see scripts/daily/setup-scheduler.ps1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

LOG_DIR="$REPO_DIR/docs/daily-logs"
DATE="$(daily_date)"
LOG_FILE="$LOG_DIR/challenges-$DATE.log"

cd "$REPO_DIR"
mkdir -p "$LOG_DIR"

log_line "$LOG_FILE" "Starting challenge-assumptions run..."
trap 'exit_code=$?; log_exit_status "$LOG_FILE" "challenge-assumptions" "$exit_code"' EXIT

CLAUDE_BIN="$(ensure_claude_bin "$LOG_FILE")"
log_line "$LOG_FILE" "Using Claude CLI: $CLAUDE_BIN"

"$CLAUDE_BIN" -p "
Run /challenge-assumptions for articles updated in the last 7 days.

Context:
- Repo is at: $REPO_DIR
- Today's date: $DATE
- Read CLAUDE.md and knowledge-base/INDEX.md before starting
- Follow the full workflow in .claude/skills/challenge-assumptions/SKILL.md
- Only challenge articles whose 'created' or 'updated' frontmatter date is within the last 7 days
- Skip any article that already has a '## Challenges' section
- Append the challenges section to each qualifying article
- Update frontmatter: set 'challenged' and bump 'updated' to today

Output the final summary table when complete.
" \
  --dangerously-skip-permissions \
  >> "$LOG_FILE" 2>&1

log_line "$LOG_FILE" "Challenge-assumptions run complete. Log: $LOG_FILE"
