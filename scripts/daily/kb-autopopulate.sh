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

# Capture starting SHA so end-of-run inventory knows what changed
START_SHA="$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || echo "unknown")"
log_line "$LOG_FILE" "Starting SHA: $START_SHA"

# Pull latest before discovering (avoids merge conflicts on commit)
git_pull_if_clean "$LOG_FILE"

# Step 1: kb-discover — search web, dedup, ingest top matches to raw/
#
# NON-INTERACTIVE PROMPT: cron has no user to answer clarifying questions.
# All scope decisions are pre-specified. Override no-assumptions rule.
log_line "$LOG_FILE" "Running /kb-discover via headless Claude..."
DISCOVER_PROMPT='HEADLESS CRON RUN — no user to answer questions. Execute without asking. Apply these defaults:

TASK: Auto-populate the knowledge base from knowledge-base/sources.yaml.

TOOLS: Use agent-browser via Bash if available (`agent-browser fetch <url>` and `agent-browser search <query>`). If agent-browser unavailable, use WebFetch tool as the primary fallback. curl -sL is a last resort only.

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
  --allowedTools Bash,Read,Write,Edit,Glob,Grep,WebFetch \
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
- **MANDATORY**: Update knowledge-base/INDEX.md after EACH article. Read INDEX.md, find the right `### <Category>` header, append a new bullet in the format `- [Title](wiki/category/slug.md) — one-line summary. Tags: tag1, tag2`. Increment `Total articles: N` in Statistics section. If you skip INDEX update, the run is INVALID — article is orphaned from the catalog.
- Generate Voyage AI embedding (voyage-3-lite, 512-dim) via Supabase MCP and upsert into `kb_articles` table. Real schema (see migrations/081-kb-articles-and-sources.sql): `slug UNIQUE, title, category, summary, content, embedding vector(512), source_urls TEXT[], tags TEXT[], word_count INT`. Use `INSERT ... ON CONFLICT (slug) DO UPDATE` so re-runs are idempotent. If Supabase MCP is unreachable, skip embedding but continue with markdown compile — log embedding_errors=N.
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

# Step 3: Inventory what changed during this run
#
# The auto-commit Stop hook (scripts/claude-hooks/auto-commit.sh) fires after
# each `claude -p` subagent finishes and creates its own commits. So by this
# point, changes may already be committed. We just need to:
#   (a) Count what was ingested/compiled (for log.md summary)
#   (b) Commit any remaining uncommitted changes (edge case)
#   (c) Push once at the end
TIMESTAMP="$(date '+%Y-%m-%d %H:%M')"
COMMITS_SINCE_START="$(git -C "$REPO_DIR" log "$START_SHA..HEAD" --oneline 2>/dev/null | wc -l)"
NEW_RAW_COUNT="$(git -C "$REPO_DIR" diff --name-only "$START_SHA" HEAD 2>/dev/null | grep -c '^knowledge-base/raw/' || true)"
NEW_WIKI_COUNT="$(git -C "$REPO_DIR" diff --name-only "$START_SHA" HEAD 2>/dev/null | grep -c '^knowledge-base/wiki/' || true)"
UNCOMMITTED="$(git -C "$REPO_DIR" status --porcelain 2>/dev/null | wc -l)"

log_line "$LOG_FILE" "Inventory: commits=$COMMITS_SINCE_START raw_changed=$NEW_RAW_COUNT wiki_changed=$NEW_WIKI_COUNT uncommitted=$UNCOMMITTED"

# Step 4: Commit any lingering uncommitted changes (edge case — auto-commit should handle most)
if [ "$UNCOMMITTED" -gt 0 ]; then
  git -C "$REPO_DIR" add knowledge-base/ 2>/dev/null || true
  git -C "$REPO_DIR" commit -m "kb(auto): populate from sources.yaml ($TIMESTAMP)" \
    --no-verify 2>&1 | tail -3 >> "$LOG_FILE" \
    || log_line "$LOG_FILE" "Final commit skipped (nothing to commit or hook blocked)"
fi

# Step 5: Append summary to knowledge-base/log.md (Karpathy chronological log)
# Only append if something actually happened this run
if [ "$COMMITS_SINCE_START" -gt 0 ] || [ "$UNCOMMITTED" -gt 0 ]; then
  {
    echo ""
    echo "## [$TIMESTAMP] discover+compile | cron $HOUR:00 | commits=$COMMITS_SINCE_START raw=$NEW_RAW_COUNT wiki=$NEW_WIKI_COUNT"
  } >> "$KB_LOG"
  # Commit the log append itself
  git -C "$REPO_DIR" add knowledge-base/log.md 2>/dev/null || true
  git -C "$REPO_DIR" commit -m "kb(log): append run summary $TIMESTAMP" --no-verify 2>&1 | tail -1 >> "$LOG_FILE" || true
fi

# Step 6: Push once — catches commits from auto-commit hook + any from this script
# Retry once on failure (transient network / rebase needed)
log_line "$LOG_FILE" "Pushing to origin/main..."
if ! git -C "$REPO_DIR" push origin main 2>&1 | tail -3 >> "$LOG_FILE"; then
  log_line "$LOG_FILE" "Push failed — trying pull --rebase then push again"
  git -C "$REPO_DIR" pull --rebase origin main 2>&1 | tail -3 >> "$LOG_FILE" || true
  git -C "$REPO_DIR" push origin main 2>&1 | tail -3 >> "$LOG_FILE" \
    || log_line "$LOG_FILE" "Push failed twice — will retry next run"
fi

log_line "$LOG_FILE" "KB auto-populate complete. Commits this run: $COMMITS_SINCE_START"
