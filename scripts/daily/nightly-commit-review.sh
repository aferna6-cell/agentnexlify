#!/usr/bin/env bash
# nightly-commit-review.sh — manual trigger for the nightly commit-review agent.
# The scheduled-tasks MCP fires this autonomously at 2:37 AM local daily.
# Run manually to test or to catch up after a missed night.
#
# Usage:
#   bash scripts/daily/nightly-commit-review.sh           # last 24h
#   bash scripts/daily/nightly-commit-review.sh 48        # last 48h
#   CLAUDE_NIGHTLY_REVIEW=0 bash ...                      # no-op kill switch
#
# Full scope + guardrails: .claude/skills/nightly-commit-review/SKILL.md

set -euo pipefail

HOURS="${1:-24}"
TODAY="$(date +%Y-%m-%d)"
REPO_ROOT="$(git rev-parse --show-toplevel)"
REPORT_DIR="$REPO_ROOT/docs/dev-knowledge/nightly-reviews"
REPORT="$REPORT_DIR/$TODAY.md"

mkdir -p "$REPORT_DIR"

if [[ "${CLAUDE_NIGHTLY_REVIEW:-1}" == "0" ]]; then
  echo "CLAUDE_NIGHTLY_REVIEW=0 — skipping nightly review"
  exit 0
fi

cd "$REPO_ROOT"

echo "=== Nightly commit review — last ${HOURS}h ==="
echo "Report → $REPORT"

# Safety: don't run on uncommitted changes
if [[ -n "$(git status --porcelain)" ]]; then
  echo "WARN: working tree dirty — aborting to avoid mixing manual + auto changes"
  exit 1
fi

# Pull latest so we're reviewing current state
git fetch origin main
git pull --rebase origin main

COMMITS="$(git log --since="${HOURS} hours ago" --oneline --no-merges)"

if [[ -z "$COMMITS" ]]; then
  cat > "$REPORT" <<EOF
# Nightly Review — $TODAY

No commits in last ${HOURS}h. Nothing to review.
EOF
  echo "No commits in window. Empty report written."
  exit 0
fi

echo ""
echo "Commits in window:"
echo "$COMMITS"
echo ""

# Invoke Claude Code via pinned v2.1.98 runner with the review prompt.
# The skill file has the full prompt; we just reference it.
PROMPT="Read .claude/skills/nightly-commit-review/SKILL.md and execute the Scheduled Task Prompt section for the last ${HOURS} hours of commits. Write report to $REPORT. Respect every guardrail."

# If claude CLI is available, invoke it. Otherwise, dump prompt for manual paste.
if command -v claude >/dev/null 2>&1; then
  echo "$PROMPT" | claude -p --allowedTools Bash,Read,Write,Edit,Glob,Grep
else
  echo "claude CLI not found on PATH. Manual prompt below — paste into Claude Code:"
  echo ""
  echo "---"
  echo "$PROMPT"
  echo "---"
  exit 2
fi

echo "Done. Report: $REPORT"
