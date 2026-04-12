#!/usr/bin/env bash
# KB Auto-Populate — scheduled twice daily (6am + 6pm)
# Runs /kb-discover to find new articles matching sources.yaml, then /kb-compile
# to promote raw → wiki with embeddings. Commits any new content to git.
#
# Cron (installed by scripts/daily/setup-cron.sh):
#   0 6,18 * * * cd /home/aidan/agentnexlify && bash scripts/daily/kb-autopopulate.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
COMMON_SH="$REPO_DIR/scripts/daily/common.sh"
# shellcheck source=./common.sh
source "$COMMON_SH"

LOG_DIR="$REPO_DIR/docs/daily-logs"
DATE="$(daily_date)"
HOUR="$(date +%H)"
LOG_FILE="$LOG_DIR/kb-autopop-$DATE-$HOUR.log"
KB_LOG="$REPO_DIR/knowledge-base/log.md"

cd "$REPO_DIR"
mkdir -p "$LOG_DIR"

log_line "$LOG_FILE" "Starting KB auto-populate ($HOUR:00)..."
trap 'exit_code=$?; log_exit_status "$LOG_FILE" "KB auto-populate" "$exit_code"' EXIT

# Pull latest before discovering (avoids merge conflicts on commit)
git_pull_if_clean "$LOG_FILE"

# Step 1: kb-discover — search web, dedup, ingest top matches to raw/
log_line "$LOG_FILE" "Running /kb-discover via headless Claude..."
DISCOVER_PROMPT="Run /kb-discover across all categories in knowledge-base/sources.yaml. For each category: search the web using agent-browser, score results for relevance to AgentNexLiFy, deduplicate against knowledge-base/known-urls.json, and ingest the top 2 new articles per category into knowledge-base/raw/<category>/. Append ingested URLs to known-urls.json. Print a summary: categories processed, articles ingested, articles rejected."

claude -p "$DISCOVER_PROMPT" \
  --allowedTools Bash,Read,Write,Edit,Glob,Grep \
  >> "$LOG_FILE" 2>&1 || log_line "$LOG_FILE" "kb-discover step failed (non-fatal)"

# Step 2: kb-compile — process PENDING.md raw files into wiki/ with embeddings
log_line "$LOG_FILE" "Running /kb-compile on pending sources..."
COMPILE_PROMPT="Run /kb-compile. For each file listed in knowledge-base/PENDING.md: read the raw source, generate a Karpathy-pattern wiki article using the template at .claude/skills/wiki/references/template.md, cross-reference existing wiki pages via [[slug]] links, update knowledge-base/INDEX.md with the new entry, generate a Voyage AI embedding (voyage-3-lite, 512-dim), and store in Supabase kb_articles table. Remove processed entries from PENDING.md. Print: articles compiled, wiki pages touched, embeddings stored."

claude -p "$COMPILE_PROMPT" \
  --allowedTools Bash,Read,Write,Edit,Glob,Grep,mcp__supabase__* \
  >> "$LOG_FILE" 2>&1 || log_line "$LOG_FILE" "kb-compile step failed (non-fatal)"

# Step 3: Append summary to knowledge-base/log.md (Karpathy chronological log)
TIMESTAMP="$(date '+%Y-%m-%d %H:%M')"
NEW_RAW_COUNT="$(git -C "$REPO_DIR" status --short knowledge-base/raw/ 2>/dev/null | wc -l)"
NEW_WIKI_COUNT="$(git -C "$REPO_DIR" status --short knowledge-base/wiki/ 2>/dev/null | wc -l)"

if [ "$NEW_RAW_COUNT" -gt 0 ] || [ "$NEW_WIKI_COUNT" -gt 0 ]; then
  {
    echo ""
    echo "## [$TIMESTAMP] discover+compile | cron $HOUR:00 | raw=$NEW_RAW_COUNT wiki=$NEW_WIKI_COUNT"
  } >> "$KB_LOG"
  log_line "$LOG_FILE" "Appended to knowledge-base/log.md: raw=$NEW_RAW_COUNT wiki=$NEW_WIKI_COUNT"
else
  log_line "$LOG_FILE" "No changes detected — skipping log.md append and commit"
  exit 0
fi

# Step 4: Commit + push new content (if any)
if [ -n "$(git -C "$REPO_DIR" status --short knowledge-base/ 2>/dev/null)" ]; then
  git -C "$REPO_DIR" add knowledge-base/
  git -C "$REPO_DIR" commit -m "$(cat <<EOF
kb(auto): populate from sources.yaml ($TIMESTAMP)

Scheduled auto-populate: /kb-discover + /kb-compile
raw=$NEW_RAW_COUNT  wiki=$NEW_WIKI_COUNT

EOF
)" >> "$LOG_FILE" 2>&1 || log_line "$LOG_FILE" "Commit failed (maybe pre-commit hook blocked)"

  git -C "$REPO_DIR" push origin main >> "$LOG_FILE" 2>&1 \
    || log_line "$LOG_FILE" "Push failed (will retry next run)"
fi

log_line "$LOG_FILE" "KB auto-populate complete."
