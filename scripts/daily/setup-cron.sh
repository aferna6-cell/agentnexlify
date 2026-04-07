#!/usr/bin/env bash
# Set up cron jobs for automated morning/evening routines
# Works on Linux, macOS, and WSL

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
MORNING_SCRIPT="$REPO_DIR/scripts/daily/morning-auto.sh"
EVENING_SCRIPT="$REPO_DIR/scripts/daily/evening-auto.sh"
SMOKE_SCRIPT="$REPO_DIR/scripts/daily/e2e-smoke.sh"
CHALLENGES_SCRIPT="$REPO_DIR/scripts/daily/challenge-assumptions.sh"

# Default times
MORNING_HOUR="${1:-8}"
MORNING_MIN="${2:-0}"
EVENING_HOUR="${3:-20}"
EVENING_MIN="${4:-0}"

echo "AgentNexLiFy Cron Setup"
echo "======================="
echo "Repo: $REPO_DIR"
echo "Morning: $MORNING_HOUR:$(printf '%02d' $MORNING_MIN)"
echo "Evening: $EVENING_HOUR:$(printf '%02d' $EVENING_MIN)"
echo ""

# Make scripts executable
chmod +x "$MORNING_SCRIPT"
chmod +x "$EVENING_SCRIPT"
chmod +x "$SMOKE_SCRIPT"
chmod +x "$CHALLENGES_SCRIPT"

# Check if claude is available
if ! command -v claude &> /dev/null; then
    echo "ERROR: claude CLI not found. Install: npm install -g @anthropic-ai/claude-code"
    exit 1
fi
CLAUDE_BIN="$(command -v claude)"
echo "Claude Code found: $CLAUDE_BIN"

TMP_CRONTAB="$(mktemp)"
trap 'rm -f "$TMP_CRONTAB"' EXIT

# Remove existing AgentNexLiFy cron entries
crontab -l 2>/dev/null | grep -v "AgentNexLiFy" > "$TMP_CRONTAB" 2>/dev/null || true

printf -v morning_cmd 'cd %q && bash %q' "$REPO_DIR" "$MORNING_SCRIPT"
printf -v evening_cmd 'cd %q && bash %q' "$REPO_DIR" "$EVENING_SCRIPT"
printf -v claude_bin_q '%q' "$CLAUDE_BIN"

# Add new entries
echo "# AgentNexLiFy Morning Startup (weekdays)" >> "$TMP_CRONTAB"
printf '%s %s * * 1-5 AGENTNEXLIFY_CLAUDE_BIN=%s bash -lc %q # AgentNexLiFy-Morning\n' "$MORNING_MIN" "$MORNING_HOUR" "$claude_bin_q" "$morning_cmd" >> "$TMP_CRONTAB"

echo "# AgentNexLiFy Evening Review (weekdays)" >> "$TMP_CRONTAB"
printf '%s %s * * 1-5 AGENTNEXLIFY_CLAUDE_BIN=%s bash -lc %q # AgentNexLiFy-Evening\n' "$EVENING_MIN" "$EVENING_HOUR" "$claude_bin_q" "$evening_cmd" >> "$TMP_CRONTAB"

printf -v smoke_cmd 'cd %q && bash %q' "$REPO_DIR" "$SMOKE_SCRIPT"
echo "# AgentNexLiFy Nightly E2E Smoke Test (daily)" >> "$TMP_CRONTAB"
printf '0 6 * * * bash -lc %q # AgentNexLiFy-E2E-Smoke\n' "$smoke_cmd" >> "$TMP_CRONTAB"

printf -v challenges_cmd 'cd %q && bash %q' "$REPO_DIR" "$CHALLENGES_SCRIPT"
echo "# AgentNexLiFy Challenge Assumptions — 9 PM daily (after evening review)" >> "$TMP_CRONTAB"
printf '0 21 * * * AGENTNEXLIFY_CLAUDE_BIN=%s bash -lc %q # AgentNexLiFy-ChallengeAssumptions\n' "$claude_bin_q" "$challenges_cmd" >> "$TMP_CRONTAB"

# Install
crontab "$TMP_CRONTAB"

echo ""
echo "Cron jobs installed:"
crontab -l | grep "AgentNexLiFy"
echo ""
echo "To remove: crontab -l | grep -v AgentNexLiFy | crontab -"
echo ""
echo "IMPORTANT: Machine must be on at scheduled times."
echo "Logs: docs/daily-logs/auto-morning-*.log, auto-evening-*.log, challenges-*.log"
