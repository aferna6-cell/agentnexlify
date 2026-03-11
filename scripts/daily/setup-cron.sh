#!/usr/bin/env bash
# Set up cron jobs for automated morning/evening routines
# Works on Linux, macOS, and WSL

set -e

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
MORNING_SCRIPT="$REPO_DIR/scripts/daily/morning-auto.sh"
EVENING_SCRIPT="$REPO_DIR/scripts/daily/evening-auto.sh"

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

# Check if claude is available
if ! command -v claude &> /dev/null; then
    echo "ERROR: claude CLI not found. Install: npm install -g @anthropic-ai/claude-code"
    exit 1
fi
echo "Claude Code found: $(which claude)"

# Remove existing AgentNexLiFy cron entries
crontab -l 2>/dev/null | grep -v "AgentNexLiFy" > /tmp/crontab_clean 2>/dev/null || true

# Add new entries
echo "# AgentNexLiFy Morning Startup (weekdays)" >> /tmp/crontab_clean
echo "$MORNING_MIN $MORNING_HOUR * * 1-5 cd $REPO_DIR && bash $MORNING_SCRIPT # AgentNexLiFy-Morning" >> /tmp/crontab_clean

echo "# AgentNexLiFy Evening Review (weekdays)" >> /tmp/crontab_clean
echo "$EVENING_MIN $EVENING_HOUR * * 1-5 cd $REPO_DIR && bash $EVENING_SCRIPT # AgentNexLiFy-Evening" >> /tmp/crontab_clean

# Install
crontab /tmp/crontab_clean
rm /tmp/crontab_clean

echo ""
echo "Cron jobs installed:"
crontab -l | grep "AgentNexLiFy"
echo ""
echo "To remove: crontab -l | grep -v AgentNexLiFy | crontab -"
echo ""
echo "IMPORTANT: Machine must be on at scheduled times."
echo "Logs: docs/daily-logs/auto-morning-*.log and auto-evening-*.log"
