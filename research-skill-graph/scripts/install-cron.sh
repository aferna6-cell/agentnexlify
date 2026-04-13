#!/usr/bin/env bash
# Non-destructive cron installer. Preserves existing crontab.
# Adds (if not already present) a line to run the research engine every 6 hours.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LINE="0 */6 * * * $ROOT/scripts/run-research.sh --auto-commit >> /tmp/research.log 2>&1"
MARKER="# research-skill-graph"

existing=$(crontab -l 2>/dev/null || true)

if grep -F "$MARKER" <<< "$existing" >/dev/null 2>&1; then
  echo "cron entry already present — nothing to do"
  exit 0
fi

{
  printf '%s\n' "$existing"
  printf '\n%s\n%s\n' "$MARKER" "$LINE"
} | crontab -

echo "installed cron entry (runs every 6 hours):"
echo "  $LINE"
echo
echo "check with: crontab -l"
echo "ensure cron daemon is running: sudo service cron start"
