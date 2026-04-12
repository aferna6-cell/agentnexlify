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

# Resolve claude binary (cron has minimal PATH — same pattern as morning-auto.sh)
CLAUDE_BIN="$(resolve_claude_bin 2>/dev/null || true)"
if [ -z "$CLAUDE_BIN" ] || [ ! -x "$CLAUDE_BIN" ]; then
  log_line "$LOG_FILE" "ERROR: claude CLI not found. Set AGENTNEXLIFY_CLAUDE_BIN in cron entry."
  exit 1
fi
log_line "$LOG_FILE" "Using claude: $CLAUDE_BIN"

# Pull latest before discovering (avoids merge conflicts on commit)
git_pull_if_clean "$LOG_FILE"

# Step 1: kb-discover — search web, dedup, ingest top matches to raw/
#
# NON-INTERACTIVE PROMPT: cron has no user to answer clarifying questions.
# All scope decisions are pre-specified. Override no-assumptions rule.
log_line "$LOG_FILE" "Running /kb-discover via headless Claude..."
DISCOVER_PROMPT='HEADLESS CRON RUN — no user to answer questions. Execute without asking. Apply these defaults:

TASK: Auto-populate the knowledge base from knowledge-base/sources.yaml.

TOOLS: Use agent-browser via Bash (per CLAUDE.md rule: NEVER use WebFetch/WebSearch). Command: `agent-browser fetch <url>` and `agent-browser search <query>`. If agent-browser unavailable, use `curl -sL` to fetch URLs directly.

SCOPE (locked — do not ask, do not override):
- Process ALL 7 categories in sources.yaml
- Per category: run top 3 search queries from the file, pick top 2 NEW articles by relevance
- Max 14 new articles total this run (2 per category × 7 categories)
- Dedup against knowledge-base/known-urls.json before writing anything
- Skip categories that have no new unique URLs — do not retry

RELEVANCE FILTER (apply BEFORE fetching — reject obvious junk):
- Must relate to AI, SaaS, the specified category, or AgentNexLiFy stack (FastAPI, Supabase, Vercel, Railway, Anthropic)
- REJECT: sports leagues (P.LEAGUE, EASL), drug pricing (340B), unrelated nonprofits (Front Porch Forum), generic AI research papers that don'\''t apply to small business
- REJECT: blog/vendor homepages with no article content (e.g. anthropic.com homepage, gohighlevel home-page-ver3)
- PREFER: specific articles with a publish date, technical depth, or competitive/regulatory relevance
- If a category has no passing URLs after filtering, SKIP it — better to ingest 4 good articles than 14 noisy ones
- Always add REJECTED urls to known-urls.json so they won'\''t be retried next run

PER ARTICLE:
1. Fetch URL → convert to markdown (strip nav/ads)
2. Write to knowledge-base/raw/<category>/<slug>.md with frontmatter: source_url, fetched_at, category
3. Append URL to knowledge-base/known-urls.json (JSON array — read, append, rewrite)
4. Append entry to knowledge-base/PENDING.md for the compile step

OUTPUT: single summary block at end:
  categories_processed=N  urls_fetched=N  new_raw_files=N  deduped=N  errors=N

DO NOT ask clarifying questions. DO NOT run Playwright (not allowed here). DO NOT touch knowledge-base/wiki/ — that is compile`\''s job. Use confidence >=80% to proceed; if genuinely blocked, print BLOCKED: <reason> and exit.'

"$CLAUDE_BIN" -p "$DISCOVER_PROMPT" \
  --allowedTools Bash,Read,Write,Edit,Glob,Grep \
  --permission-mode bypassPermissions \
  >> "$LOG_FILE" 2>&1 || log_line "$LOG_FILE" "kb-discover step failed (non-fatal)"

# Step 2: kb-compile — process PENDING.md raw files into wiki/ with embeddings
log_line "$LOG_FILE" "Running /kb-compile on pending sources..."
COMPILE_PROMPT='HEADLESS CRON RUN — no user to answer questions. Execute without asking.

TASK: Compile all pending raw sources into wiki articles.

SCOPE (locked):
- Read knowledge-base/PENDING.md — if empty, print `no pending sources` and exit 0
- Process UP TO 4 entries from PENDING.md per run (context cap — leave the rest for next run)
- For each listed raw file, generate ONE wiki article
- Use template at .claude/skills/wiki/references/template.md
- Write to knowledge-base/wiki/<category>/<slug>.md
- Cross-reference existing wiki pages via [[slug]] inline links (≥1 per article)
- Update knowledge-base/INDEX.md (add entry under the right category section)
- Generate Voyage AI embedding (voyage-3-lite, 512-dim) via Supabase MCP and store in kb_articles table (columns: slug, title, category, content, embedding, source_url, created_at). If Supabase MCP is unreachable, skip embedding but continue with markdown compile — log embedding_errors=N.
- After EACH successful compile, remove that specific entry from PENDING.md (edit the file, do not batch)

DO NOT:
- Modify knowledge-base/raw/ (source of truth — read-only)
- Ask clarifying questions
- Exceed the 4-entry cap — partial progress is expected

OUTPUT: single summary:
  pending_count=N  compiled=N  wiki_pages_touched=N  embeddings_stored=N  errors=N'

"$CLAUDE_BIN" -p "$COMPILE_PROMPT" \
  --allowedTools Bash,Read,Write,Edit,Glob,Grep,mcp__supabase__* \
  --permission-mode bypassPermissions \
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
