#!/usr/bin/env bash
# Friday reading routine.
#
# Skims the curated AI/agent feed list (Anthropic eng blog, Simon Willison,
# Latent Space, etc.) and drops a fresh markdown digest into
# knowledge-base/raw/weekly/. Subsequent /kb-compile turns it into a wiki entry.
#
# Manual run:    bash scripts/daily/friday-reading.sh
# Scheduled run: cron / Task Scheduler weekly Friday 8am
# Disable:       export FRIDAY_READING=0
#
# Source feed list: scripts/daily/friday-reading.sources.txt (one URL per line)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# shellcheck source=common.sh
source "$REPO_ROOT/scripts/daily/common.sh"

LOG_DIR="$REPO_ROOT/logs"
LOG_FILE="$LOG_DIR/friday-reading.log"
mkdir -p "$LOG_DIR"

OUTPUT_DIR="$REPO_ROOT/knowledge-base/raw/weekly"
mkdir -p "$OUTPUT_DIR"

DATE_STAMP="$(daily_date)"
OUTPUT_FILE="$OUTPUT_DIR/digest-${DATE_STAMP}.md"

SOURCES_FILE="$REPO_ROOT/scripts/daily/friday-reading.sources.txt"

if [ "${FRIDAY_READING:-1}" = "0" ]; then
    log_line "$LOG_FILE" "Friday reading disabled via FRIDAY_READING=0."
    exit 0
fi

if [ ! -f "$SOURCES_FILE" ]; then
    log_line "$LOG_FILE" "ERROR: source list missing at $SOURCES_FILE"
    exit 1
fi

CLAUDE_BIN="$(ensure_claude_bin "$LOG_FILE")" || exit 1

log_line "$LOG_FILE" "Friday reading start (digest -> $OUTPUT_FILE)"

PROMPT_FILE="$(mktemp -t friday-reading-prompt.XXXXXX)"
trap 'rm -f "$PROMPT_FILE"' EXIT

{
    echo "You are running the Friday reading routine for AgentNexLiFy."
    echo
    echo "Goal: produce a tight markdown digest of the most relevant AI/agent"
    echo "writing this week. Audience is a single engineer; ruthless filter."
    echo
    echo "Sources to scan (use agent-browser or WebFetch as available):"
    echo
    while IFS= read -r url; do
        case "$url" in
            ''|\#*) continue ;;
            *) echo "- $url" ;;
        esac
    done < "$SOURCES_FILE"
    echo
    echo "Process:"
    echo "1. Fetch each source. Skim posts published in the last 7 days."
    echo "2. Apply the agent-filter 5-test (see .claude/skills/agent-filter/SKILL.md):"
    echo "   matters in 2yr, real postmortem, no re-platform, real skip-cost, measurable."
    echo "3. Pick the top 3 items. Drop the rest."
    echo
    echo "Output: write a single markdown file to $OUTPUT_FILE with this shape:"
    echo
    echo "---"
    echo "title: Friday reading $DATE_STAMP"
    echo "category: ai-llm"
    echo "tags: [weekly-digest]"
    echo "created: $DATE_STAMP"
    echo "---"
    echo
    echo "# Friday Reading — $DATE_STAMP"
    echo
    echo "## 1. <headline>"
    echo "- Source: <url>"
    echo "- Why it matters: <1-2 sentences, AgentNexLiFy-specific>"
    echo "- Action: <concrete change or decision> OR <none — context only>"
    echo
    echo "(repeat for items 2 and 3)"
    echo
    echo "## Skipped this week"
    echo "- <one-line reason per item that almost made the cut>"
    echo
    echo "Constraints:"
    echo "- Caveman tone (drop articles, fragments OK, technical terms exact)"
    echo "- No marketing speak, no hype"
    echo "- If nothing meets the bar, write 'No qualifying items this week.' and exit"
    echo "- Do not commit anything; the daily routine handles git separately"
} > "$PROMPT_FILE"

if "$CLAUDE_BIN" --print < "$PROMPT_FILE" >> "$LOG_FILE" 2>&1; then
    log_line "$LOG_FILE" "Friday reading wrote digest to $OUTPUT_FILE"
else
    EXIT_CODE=$?
    log_line "$LOG_FILE" "Friday reading FAILED with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
