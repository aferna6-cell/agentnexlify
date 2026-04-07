# Claudeopedia — Personal Knowledge Base System

**Spec Version:** 1.0
**Date:** 2026-04-06
**Status:** Ready to execute

---

## Overview

Claudeopedia extends the existing `knowledge-base/` infrastructure (kb-ingest, kb-compile, kb-query, kb-health, kb-discover) with five new components that make the knowledge base a living, queryable, self-challenging personal wiki. The name is a portmanteau of Claude + encyclopedia.

The existing KB pipeline is **source-centric**: discover sources, ingest raw files, compile into wiki articles, query with embeddings. Claudeopedia adds a **thought-centric** layer: any input (screenshot, URL, raw text, file, video) becomes a structured wiki entry in one step, the accumulated knowledge is periodically synthesized and challenged, and the whole thing is browsable in a local viewer.

---

## Design Decisions (Apply to All Components)

1. **Article format is sacred.** Every component that writes wiki articles uses the same Karpathy-style template (Section 6 below). No exceptions.
2. **Reuse existing embedding infrastructure.** All embedding goes through `backend/services/embeddings.py` (Voyage AI, voyage-3-lite, 512-dim). All storage goes to the `kb_articles` table in Supabase via the same SQL patterns as kb-compile.
3. **Reuse existing categories.** The 7 categories from kb-ingest (`competitors`, `ai-llm`, `small-biz-saas`, `verticals`, `technical`, `regulations`, `growth`) plus a new `general` category for personal/miscellaneous knowledge that doesn't fit the existing taxonomy.
4. **INDEX.md is the single source of truth** for the article catalog. Every component that creates or modifies articles must update INDEX.md.
5. **No new database tables.** The existing `kb_articles` and `kb_sources` tables are sufficient. The `challenges` cron appends to existing articles rather than creating separate records.
6. **Dark theme everywhere.** The viewer matches the dashboard's dark theme.
7. **Obsidian compatibility is non-destructive.** The `--obsidian` flag copies files; it never modifies the canonical wiki.

---

## Section 1: `/wiki` Skill

### File to Create

```
.claude/skills/wiki/SKILL.md
```

### Purpose

One-command ingestion of ANY input into a Karpathy-style wiki article. Unlike `/kb-ingest` (which saves raw and defers compilation to `/kb-compile`), `/wiki` goes raw-to-wiki in a single invocation. It is the "fast path" for capturing knowledge.

### Usage

```
/wiki <input> [category]
```

Where `<input>` is one of:
- A screenshot path: `/wiki /tmp/screenshot.png`
- A URL: `/wiki https://arxiv.org/abs/2401.12345`
- A YouTube URL: `/wiki https://youtube.com/watch?v=abc123`
- Raw text (quoted): `/wiki "Transformers use self-attention to..."`
- A file path: `/wiki ./notes/meeting-notes.md`
- No argument (reads clipboard or prompts): `/wiki` then paste

And `[category]` is optional (auto-detected if omitted):
- `competitors`, `ai-llm`, `small-biz-saas`, `verticals`, `technical`, `regulations`, `growth`, `general`

### Skill File Contents

```yaml
---
name: wiki
description: "Capture any input (screenshot, URL, text, file, YouTube) into a Karpathy-style wiki article. One-step raw-to-wiki."
user_invocable: true
---
```

### Workflow (Step by Step)

**Step 1: Detect Input Type**

Parse the argument to determine input type:
- Starts with `http://` or `https://` and contains `youtube.com` or `youtu.be` → YouTube
- Starts with `http://` or `https://` → URL
- Ends with `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp` → Screenshot
- Is a valid file path that exists on disk → File
- Everything else → Raw text
- No argument → Prompt user to paste text

**Step 2: Extract Content**

Based on input type:

| Type | Extraction Method |
|------|-------------------|
| Screenshot | Read the image file with the Read tool. Claude extracts all visible text, diagrams, code, and context from the image. |
| URL | Use WebFetch to retrieve page content. Strip navigation, ads, sidebars. Extract title, body, publication date. |
| YouTube | Use WebFetch on the YouTube URL to get the page. Extract video title, channel, description. If a transcript is available (check for transcript in page content), extract it. If not, note that no transcript was available and work from title + description. |
| File | Read the file with the Read tool. Preserve any existing structure. |
| Raw text | Use the text directly. |

**Step 3: Determine Category**

If category was provided as argument, use it.

If not, read the extracted content and assign to one of the 8 categories based on content analysis:
- `competitors` — About specific competitor companies, market positioning, feature comparisons
- `ai-llm` — About AI models, LLM capabilities, prompt engineering, agent architectures
- `small-biz-saas` — About SaaS business models, pricing, churn, PLG strategies
- `verticals` — About specific industries (contractors, dental, salon, legal, restaurant, real estate, fitness)
- `technical` — About software engineering patterns, database design, embeddings, streaming, infrastructure
- `regulations` — About compliance (HIPAA, TCPA, GDPR), data privacy, AI disclosure laws
- `growth` — About distribution, virality, SEO, GEO, partnerships, marketing
- `general` — Personal learning, research, concepts that don't fit the above

**Step 4: Check for Existing Article**

Read `knowledge-base/INDEX.md`. Check if an article already exists that covers the same entity, concept, or topic.

Decision logic:
- If an existing article covers the SAME entity (e.g., ingesting a new GoHighLevel article when `gohighlevel.md` exists) → **merge** into the existing article (update content, add to sources list, bump `updated` date)
- If the input covers a NEW concept/entity → **create** a new article
- If uncertain → **create** a new article (better to have two articles than to corrupt one)

**Step 5: Generate Article**

Using the extracted content as source material, write a wiki article following the Karpathy Article Template (Section 6 of this spec). This is the core creative step.

Key principles for article generation:
- **Dense, not fluffy.** Every sentence should contain information. No filler.
- **Essay-style, not listicle.** Paragraphs that flow logically, not bullet-point dumps (tables are fine for comparative data).
- **Opinionated where warranted.** "This matters because..." not just "This exists."
- **Cross-linked.** Reference existing wiki articles using `[[slug]]` syntax wherever relevant. Read INDEX.md to know what articles exist.
- **Source-attributed.** Specific claims cite where they came from.

**Step 6: Save Article**

Generate slug from title: lowercase, hyphens, no special chars, max 60 chars.

Write to `knowledge-base/wiki/{category}/{slug}.md`.

Also save the raw input to `knowledge-base/raw/{category}/{slug}-raw.md` with frontmatter:
```yaml
---
title: "Original Source Title"
source_url: https://... # or "screenshot", "clipboard", "local:{path}"
discovered: YYYY-MM-DD
category: category_name
relevance_score: 8
ingested_via: wiki
---
```

**Step 7: Generate Embedding**

Run Python to generate the embedding:
```python
import asyncio
import sys
sys.path.insert(0, '.')
from backend.services.embeddings import embed_text

text = "{title}\n\n{summary}\n\n{first 500 words of article body}"
embedding = asyncio.run(embed_text(text))
embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
print(embedding_str)
```

**Step 8: Store in Supabase**

Upsert into `kb_articles`:
```sql
INSERT INTO kb_articles (slug, title, category, summary, content, embedding, source_urls, tags, word_count, updated_at)
VALUES (
    '{category}/{slug}',
    '{title}',
    '{category}',
    '{one-line summary}',
    '{full markdown content}',
    '{embedding_vector}'::vector,
    ARRAY['{source_url_or_type}'],
    ARRAY['{tag1}', '{tag2}', ...],
    {word_count},
    now()
)
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    content = EXCLUDED.content,
    embedding = EXCLUDED.embedding,
    source_urls = kb_articles.source_urls || EXCLUDED.source_urls,
    tags = EXCLUDED.tags,
    word_count = EXCLUDED.word_count,
    updated_at = now();
```

Also register the raw source in `kb_sources`:
```sql
INSERT INTO kb_sources (source_url, file_path, category, relevance_score, title, discovered_at, compiled, compiled_at)
VALUES ('{source}', 'raw/{category}/{slug}-raw.md', '{category}', {score}, '{title}', now(), true, now())
ON CONFLICT (source_url) DO NOTHING;
```

**Step 9: Update INDEX.md**

Read current INDEX.md. Add or update the entry under the appropriate category section:
```markdown
- [{title}](wiki/{category}/{slug}.md) — {one-line summary}. Tags: {tag1}, {tag2}
```

Update the statistics (total articles count, last compiled date).

Rebuild the Cross-Reference Map by scanning all `[[slug]]` references across all wiki articles.

**Step 10: Update known-urls.json**

If input was a URL, append to `knowledge-base/known-urls.json`.

**Step 11: Report**

Output:
```
Wiki: **{title}** → wiki/{category}/{slug}.md
  Category: {category} | Words: {N} | Tags: {tags}
  Embedding: stored ({similarity to nearest existing article})
  Cross-links: [[article1]], [[article2]]
```

### Design Decisions

- `/wiki` bypasses the raw-then-compile two-step. It does both in one invocation. The raw file is still saved for provenance, but it's marked as `compiled: true` immediately.
- Screenshots are first-class inputs. Claude reads the image directly and extracts structured knowledge. This is critical for capturing Twitter threads, diagrams, whiteboard photos, and paper figures.
- YouTube URLs attempt transcript extraction via the page content. If no transcript is available, the article is generated from the video metadata (title, description, channel) and flagged as `transcript_unavailable: true` in frontmatter.
- The merge-vs-create decision defaults to create. It's easier to merge two articles later than to recover from a bad merge.

---

## Section 2: `/last30days` Skill

### File to Create

```
.claude/skills/last30days/SKILL.md
```

### Purpose

Synthesize the past 30 days of knowledge accumulation into a "State of Your Mind" report. Answers: What have I been learning? What patterns are emerging? What am I ignoring?

### Usage

```
/last30days                          # standard 30-day report
/last30days --compare 2026-03-01     # compare current 30 days vs 30 days ending at given date
/last30days --days 14                # override window to 14 days
```

### Skill File Contents

```yaml
---
name: last30days
description: "Synthesize recent knowledge accumulation into a 'State of Your Mind' report. Groups by theme, identifies patterns, surfaces blind spots."
user_invocable: true
---
```

### Workflow

**Step 1: Identify Recent Articles**

Read `knowledge-base/INDEX.md` to get the full article list.

For each article listed, read the frontmatter to get `created` and `updated` dates.

Filter to articles where `created` or `updated` falls within the target window (default: last 30 days from today).

Also query Supabase for completeness:
```sql
SELECT slug, title, category, tags, summary, word_count, updated_at
FROM kb_articles
WHERE updated_at >= now() - interval '30 days'
ORDER BY updated_at DESC;
```

**Step 2: Read All Matching Articles**

For each article in the window, read the full content from `knowledge-base/wiki/{slug}.md`.

**Step 3: Analyze and Synthesize**

Generate a structured analysis with these sections:

1. **Overview** — How many articles, total words, categories touched, sources used.

2. **By Category** — For each category that has activity, a 2-3 sentence summary of what was learned. Include article count and total words per category.

3. **Top Concepts Learned** — The 5-10 most significant new ideas, techniques, or facts encountered. Each gets a 2-3 sentence explanation with article citations.

4. **Surprising Insights** — Things that contradicted prior assumptions, unexpected connections between articles, or non-obvious implications. These are the most valuable part of the report.

5. **Belief Changes** — Explicit statements of "I used to think X, now I think Y" based on evidence from the articles. If no belief changes are evident, say so honestly.

6. **Knowledge Gaps** — Topics that were touched superficially but not explored deeply. Categories with zero or thin coverage. Questions raised by articles that weren't answered by other articles.

7. **Emerging Themes** — Patterns that span multiple categories. Example: "Three articles in different categories all point to the same conclusion about X."

8. **Recommendations** — 3-5 specific actions: articles to write, topics to research, existing articles to deepen, queries to run.

**Step 4: Comparison Mode (if `--compare` flag)**

If a comparison date is provided:
- Load articles from the comparison window (30 days ending at the given date)
- Generate the same analysis for the comparison window
- Add a "Delta" section comparing the two windows:
  - New categories explored
  - Categories that went dormant
  - Concept velocity (articles/week) comparison
  - Theme evolution: what was trending then vs now

**Step 5: Save Report**

Write to `knowledge-base/_outputs/YYYY-MM-DD-last30days.md`:

```yaml
---
title: "State of Your Mind — YYYY-MM-DD"
type: synthesis
window_start: YYYY-MM-DD
window_end: YYYY-MM-DD
articles_analyzed: N
total_words_analyzed: N
categories_active: N
compared_to: YYYY-MM-DD  # only if --compare was used
created: YYYY-MM-DD
---
```

**Step 6: Report**

Display the full report in the terminal, then:
```
Report saved to: knowledge-base/_outputs/YYYY-MM-DD-last30days.md
Window: {start} to {end} | Articles: {N} | Words: {N}
```

### Design Decisions

- The report reads full article content, not just summaries. This costs more tokens but produces dramatically better synthesis.
- "Belief Changes" is explicitly included even though it will often be empty. Its presence as a section trains the user to notice when their understanding shifts.
- The comparison mode uses a fixed 30-day window ending at the provided date, not a variable window. This keeps comparisons apples-to-apples.
- Reports are saved to `_outputs/` (same directory as kb-query outputs) rather than a new directory.

---

## Section 3: Interactive Viewer

### File to Create

```
knowledge-base/viewer.html
```

### Purpose

A single self-contained HTML file that renders the entire knowledge base as a browsable, searchable, filterable interface. No build step, no dependencies, no server required. Open in a browser and go.

### Design Decisions

- **Single file.** HTML + CSS + JS all inline. No external dependencies. This is critical for portability.
- **INDEX.md as data source.** The viewer embeds a parsed copy of INDEX.md as a JSON object at build time. When `/wiki` or `/kb-compile` updates INDEX.md, a small script regenerates the embedded data. Alternatively, the viewer can fetch INDEX.md via `fetch()` if served from a local server.
- **Dual mode.** If opened as a `file://` URL, uses embedded data. If served via HTTP (e.g., `python3 -m http.server`), fetches INDEX.md live and can load full article markdown.
- **Dark theme.** Matches the AgentNexLiFy dashboard: `#0f172a` background, `#1e293b` cards, `#e2e8f0` text, `#3b82f6` accents.
- **No framework.** Vanilla JS only. The viewer should load instantly.

### Layout

```
+------------------------------------------------------------------+
|  CLAUDEOPEDIA                                    [Search______]   |
+------------------------------------------------------------------+
|           |                                                       |
| CATEGORIES|  MAIN CONTENT AREA                                    |
|           |                                                       |
| [ ] All   |  [Timeline View]  [Grid View]  [Tag Cloud]           |
| [ ] comp  |                                                       |
| [ ] ai-llm|  +--------+ +--------+ +--------+ +--------+        |
| [ ] saas  |  | Card 1 | | Card 2 | | Card 3 | | Card 4 |        |
| [ ] vert  |  | Title  | | Title  | | Title  | | Title  |        |
| [ ] tech  |  | Date   | | Date   | | Date   | | Date  |        |
| [ ] regs  |  | Tags   | | Tags   | | Tags   | | Tags   |        |
| [ ] growth|  +--------+ +--------+ +--------+ +--------+        |
| [ ] genrl |                                                       |
|           |  +--------+ +--------+ +--------+                    |
| TAGS      |  | Card 5 | | Card 6 | | Card 7 |                    |
| #crm      |  +--------+ +--------+ +--------+                    |
| #ai       |                                                       |
| #saas     |  [Date Range: =====[====]================]            |
| ...       |  2026-04-01                        2026-04-06         |
|           |                                                       |
+------------------------------------------------------------------+
```

### Features

1. **Search Bar** — Instant client-side filtering on title, summary, and tags. Debounced at 150ms. Highlights matching text in results.

2. **Category Sidebar** — Checkbox filters. Multiple categories can be selected simultaneously. Shows article count per category. "All" toggles all on/off.

3. **Tag Cloud** — Rendered from all tags across all articles. Tag size proportional to frequency. Clicking a tag filters to articles with that tag. Multiple tags can be selected (AND logic).

4. **Date Range Slider** — HTML5 range input with two handles (start/end). Filters articles by `created` date. Shows selected date range as text.

5. **Grid View** (default) — Cards in a responsive CSS grid. Each card shows: title, category badge (colored), created date, first line of summary, tags as small pills.

6. **Timeline View** — Horizontal scrolling timeline. Articles plotted as dots/cards on a date axis. Grouped by month. Click a dot to see the article card expand below the timeline.

7. **Article Reader** — Click any card to open the article inline. If served via HTTP, fetches the markdown file and renders it using a minimal markdown parser (included inline — handles headers, bold, italic, links, code blocks, tables, blockquotes, lists). If opened as `file://`, shows the summary and a "open file" link.

8. **Stats Bar** — Bottom of the page: "42 articles | 85,000 words | 7 categories | Last updated: 2026-04-06"

### Data Format (Embedded JSON)

The viewer expects a `WIKI_DATA` JSON object, either embedded in the HTML or fetched from a companion `viewer-data.json` file:

```json
{
  "generated": "2026-04-06T20:00:00Z",
  "stats": {
    "total_articles": 42,
    "total_words": 85000,
    "categories": 7,
    "last_updated": "2026-04-06"
  },
  "articles": [
    {
      "slug": "competitors/competitive-landscape-march-2026",
      "title": "Competitive Landscape — March 2026",
      "category": "competitors",
      "summary": "Analysis of 8 major competitors; feature-complete, gap is engagement.",
      "tags": ["intercom", "drift", "tidio", "gohighlevel"],
      "created": "2026-04-04",
      "updated": "2026-04-04",
      "word_count": 620,
      "path": "wiki/competitors/competitive-landscape-march-2026.md",
      "cross_refs": ["gohighlevel", "customer-gaps-by-industry"]
    }
  ],
  "categories": [
    {"name": "competitors", "color": "#ef4444", "count": 8},
    {"name": "ai-llm", "color": "#8b5cf6", "count": 12},
    {"name": "small-biz-saas", "color": "#f59e0b", "count": 5},
    {"name": "verticals", "color": "#10b981", "count": 7},
    {"name": "technical", "color": "#06b6d4", "count": 6},
    {"name": "regulations", "color": "#ec4899", "count": 2},
    {"name": "growth", "color": "#f97316", "count": 3},
    {"name": "general", "color": "#6b7280", "count": 4}
  ],
  "tag_frequencies": {
    "crm": 5,
    "ai-employee": 3,
    "gohighlevel": 4
  }
}
```

### Viewer Data Generation

A small script (or a step added to `/wiki` and `/kb-compile`) regenerates `knowledge-base/viewer-data.json` whenever INDEX.md changes.

Add to the end of `/wiki` Step 9 and `/kb-compile` Step 7:

```bash
# Regenerate viewer data
python3 -c "
import json, re, os, yaml
from pathlib import Path

kb = Path('knowledge-base')
articles = []
tag_freq = {}
cat_counts = {}

for md_file in sorted(kb.glob('wiki/**/*.md')):
    if md_file.parent.name == '_outputs':
        continue
    text = md_file.read_text()
    # Parse YAML frontmatter
    if text.startswith('---'):
        _, fm, body = text.split('---', 2)
        meta = yaml.safe_load(fm)
    else:
        continue

    slug = f'{md_file.parent.name}/{md_file.stem}'
    tags = meta.get('tags', [])
    cat = meta.get('category', md_file.parent.name)

    for t in tags:
        tag_freq[t] = tag_freq.get(t, 0) + 1
    cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # Extract cross-refs
    cross_refs = re.findall(r'\[\[([^\]]+)\]\]', body)

    articles.append({
        'slug': slug,
        'title': meta.get('title', md_file.stem),
        'category': cat,
        'summary': meta.get('summary', body[:200].replace('\n', ' ').strip()),
        'tags': tags,
        'created': str(meta.get('created', '')),
        'updated': str(meta.get('updated', '')),
        'word_count': len(body.split()),
        'path': str(md_file.relative_to(kb)),
        'cross_refs': list(set(cross_refs))
    })

colors = {
    'competitors': '#ef4444', 'ai-llm': '#8b5cf6',
    'small-biz-saas': '#f59e0b', 'verticals': '#10b981',
    'technical': '#06b6d4', 'regulations': '#ec4899',
    'growth': '#f97316', 'general': '#6b7280'
}

data = {
    'generated': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
    'stats': {
        'total_articles': len(articles),
        'total_words': sum(a['word_count'] for a in articles),
        'categories': len(cat_counts),
        'last_updated': str(__import__('datetime').date.today())
    },
    'articles': articles,
    'categories': [
        {'name': c, 'color': colors.get(c, '#6b7280'), 'count': n}
        for c, n in sorted(cat_counts.items())
    ],
    'tag_frequencies': tag_freq
}

(kb / 'viewer-data.json').write_text(json.dumps(data, indent=2))
print(f'viewer-data.json: {len(articles)} articles, {sum(a[\"word_count\"] for a in articles)} words')
"
```

### Size Budget

The HTML file should be under 50KB. The inline markdown parser should be under 3KB (basic regex-based, not a full AST parser). The inline CSS should be under 5KB. Total JS under 15KB.

---

## Section 4: "Question Your Assumptions" Cron

### Files to Create

```
.claude/skills/challenge-assumptions/SKILL.md
scripts/daily/challenge-assumptions.sh
```

### Purpose

A scheduled process that reads recent wiki articles and generates steelman counterarguments, alternative explanations, and blind spots. The goal is to prevent the knowledge base from becoming an echo chamber of unchallenged assertions.

### Skill File Contents

```yaml
---
name: challenge-assumptions
description: "Generate steelman counterarguments for recent wiki articles. Prevents echo-chamber thinking by challenging assumptions in the knowledge base."
user_invocable: true
---
```

### Usage

```
/challenge-assumptions              # challenge articles from last 7 days
/challenge-assumptions --days 30    # override window
/challenge-assumptions --article wiki/competitors/gohighlevel.md  # challenge specific article
```

### Workflow

**Step 1: Select Articles**

If `--article` flag is provided, use that single article.

Otherwise, read INDEX.md and filter to articles with `created` or `updated` within the window (default: 7 days).

For each candidate article, read the full content from disk.

Skip articles that already have a `## Challenges` section (already processed).

**Step 2: Generate Challenges**

For EACH article, generate 3-5 challenges. Each challenge is one of three types:

1. **Counterargument** — A reasonable person could argue the opposite. "This article claims X, but a counterargument is Y because Z."
2. **Alternative Explanation** — The same data could support a different conclusion. "The evidence cited supports X, but it equally supports Y."
3. **Blind Spot** — Something the article doesn't consider. "This analysis doesn't account for Z, which could change the conclusion."

Requirements for challenges:
- Each challenge must be **specific** — reference exact claims from the article, not generic "but what if you're wrong."
- Each challenge must be **steelmanned** — present the strongest possible version of the counterposition, not a strawman.
- Each challenge must be **actionable** — suggest what evidence or research would resolve the question.
- Label each challenge with its type: `[Counterargument]`, `[Alternative Explanation]`, or `[Blind Spot]`.

**Step 3: Append to Articles**

For each article, append a `## Challenges` section at the end (before `## Relevance to AgentNexLiFy` if that section exists, otherwise at the very end):

```markdown
## Challenges

_Generated YYYY-MM-DD by assumption review._

1. **[Counterargument] Title of challenge.** Body of the challenge, referencing specific claims
   from the article. Evidence needed to resolve: description of what would settle this.

2. **[Blind Spot] Title of challenge.** Body of the challenge.
   Evidence needed to resolve: description.

3. **[Alternative Explanation] Title of challenge.** Body.
   Evidence needed to resolve: description.
```

**Step 4: Update Frontmatter**

Add `challenged: YYYY-MM-DD` to the article's frontmatter.

Bump `updated: YYYY-MM-DD`.

**Step 5: Report**

Output:
```
## Assumption Challenges — YYYY-MM-DD

Articles challenged: N
Total challenges generated: M

| Article | Challenges | Types |
|---------|------------|-------|
| Competitive Landscape | 4 | 2 counter, 1 blind spot, 1 alt explanation |
| Customer Gaps | 3 | 1 counter, 2 blind spots |
```

### Cron Script

`scripts/daily/challenge-assumptions.sh`:

```bash
#!/usr/bin/env bash
# Challenge Assumptions — Daily Cron
# Schedule: daily at 9 PM (after evening routine at 8 PM)
# Reads recent wiki articles and generates steelman challenges.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

source "$SCRIPT_DIR/common.sh"

LOG_FILE="$PROJECT_DIR/docs/daily-logs/$(date +%Y-%m-%d)-challenges.log"

echo "[$(date)] Challenge assumptions starting..." >> "$LOG_FILE"

# Resolve claude binary
CLAUDE_BIN=$(resolve_claude_binary)
if [ -z "$CLAUDE_BIN" ]; then
    echo "[$(date)] ERROR: Could not find claude binary" >> "$LOG_FILE"
    exit 1
fi

# Run headless
"$CLAUDE_BIN" -p "Run /challenge-assumptions for articles from the last 7 days. Output the report." \
    --max-turns 20 \
    >> "$LOG_FILE" 2>&1

echo "[$(date)] Challenge assumptions complete." >> "$LOG_FILE"
```

### Scheduling

Add to the Windows Task Scheduler (same pattern as morning/evening):
- **Task name:** `AgentNexLiFy-ChallengeAssumptions`
- **Schedule:** Daily at 9:00 PM
- **Action:** `wsl.exe bash /home/aidan/agentnexlify/scripts/daily/challenge-assumptions.sh`

Or via crontab (if using `setup-cron.sh`):
```
0 21 * * * /home/aidan/agentnexlify/scripts/daily/challenge-assumptions.sh
```

### Design Decisions

- Challenges are **appended to the original article**, not stored separately. This keeps the challenge in context next to the claims it challenges. When you re-read the article, you see the challenges immediately.
- Articles that already have a `## Challenges` section are **skipped**, not re-challenged. To re-challenge an article, manually delete the section and re-run.
- The cron runs at 9 PM, after the evening routine (8 PM). This is intentional — the evening routine may create or update articles, and the challenge cron should process the latest state.
- Only 3-5 challenges per article. More would be noise. Fewer wouldn't be useful.

---

## Section 5: Obsidian Integration

### File to Create

```
.claude/skills/obsidian-sync/SKILL.md
```

### Purpose

Copy wiki articles to an Obsidian vault in compatible format with `[[wikilinks]]`, YAML frontmatter, and proper folder structure. One-way sync: wiki is canonical, Obsidian is a read-friendly copy.

### Skill File Contents

```yaml
---
name: obsidian-sync
description: "Sync wiki articles to an Obsidian vault with wikilinks and frontmatter. One-way: wiki → Obsidian."
user_invocable: true
---
```

### Usage

```
/obsidian-sync /path/to/vault                # full sync
/obsidian-sync /path/to/vault --incremental  # only articles changed since last sync
```

Also available as a flag on `/wiki`:
```
/wiki https://example.com --obsidian /path/to/vault
```

### Workflow

**Step 1: Validate Vault Path**

Check that the path exists and contains a `.obsidian/` directory (indicating it's an Obsidian vault). If `.obsidian/` doesn't exist, ask for confirmation before proceeding ("This doesn't look like an Obsidian vault. Continue anyway?").

**Step 2: Create Folder Structure**

Create (if not exists):
```
{vault}/Claudeopedia/
{vault}/Claudeopedia/competitors/
{vault}/Claudeopedia/ai-llm/
{vault}/Claudeopedia/small-biz-saas/
{vault}/Claudeopedia/verticals/
{vault}/Claudeopedia/technical/
{vault}/Claudeopedia/regulations/
{vault}/Claudeopedia/growth/
{vault}/Claudeopedia/general/
{vault}/Claudeopedia/_outputs/
{vault}/Claudeopedia/_meta/
```

**Step 3: Convert Each Article**

For each wiki article in `knowledge-base/wiki/`:

1. **Read** the article from disk.

2. **Transform frontmatter** to Obsidian-compatible YAML:
   ```yaml
   ---
   title: "Article Title"
   category: competitors
   tags:
     - crm
     - ai-employee
     - gohighlevel
   sources:
     - "raw/competitors/source1.md"
   created: 2026-04-04
   updated: 2026-04-04
   aliases:
     - "Competitive Landscape"
     - "March 2026 Competitors"
   cssclass: claudeopedia
   ---
   ```
   Changes from wiki format:
   - `tags` as YAML list (not inline array) — Obsidian reads these as tags
   - Add `aliases` for alternative names (extracted from title variants and common references)
   - Add `cssclass: claudeopedia` for custom styling in Obsidian

3. **Convert cross-references** from `[[slug]]` to Obsidian-style `[[Title]]`:
   - Read INDEX.md to build a slug-to-title mapping
   - Replace `[[competitive-landscape-march-2026]]` with `[[Competitive Landscape — March 2026]]`
   - For slugs that don't map to a title, keep the slug as-is (Obsidian will show it as an unresolved link)

4. **Write** to `{vault}/Claudeopedia/{category}/{title}.md`
   - Filename is the article title (Obsidian convention), not the slug
   - Special characters in titles are replaced: `/` → `—`, `:` → ` —`

**Step 4: Generate MOC (Map of Content)**

Create `{vault}/Claudeopedia/Claudeopedia MOC.md`:

```markdown
---
title: Claudeopedia — Map of Content
tags:
  - MOC
  - claudeopedia
created: YYYY-MM-DD
---

# Claudeopedia

Personal knowledge base. {N} articles across {M} categories.
Last synced: YYYY-MM-DD HH:MM.

## By Category

### Competitors ({count})
- [[Competitive Landscape — March 2026]]
- [[GoHighLevel]]
...

### AI & LLM ({count})
- [[Claude Sonnet 4.6]]
...

## Recent (Last 30 Days)
- [[Article Title]] — YYYY-MM-DD
...

## Most Connected
- [[Article Title]] — referenced by {N} other articles
...
```

**Step 5: Write Sync Metadata**

Save sync state to `{vault}/Claudeopedia/_meta/sync-state.json`:
```json
{
  "last_sync": "2026-04-06T20:00:00Z",
  "articles_synced": 42,
  "vault_path": "/path/to/vault",
  "source_path": "/home/aidan/agentnexlify/knowledge-base"
}
```

Also save to `knowledge-base/.obsidian-sync-state.json` (gitignored) for incremental sync support.

**Step 6: Incremental Mode**

If `--incremental` flag:
- Read `knowledge-base/.obsidian-sync-state.json` to get `last_sync` timestamp
- Only process articles where `updated` date is after `last_sync`
- Still regenerate the MOC (it's cheap)

**Step 7: Report**

```
Obsidian sync → {vault_path}/Claudeopedia/
  Articles synced: 42 (3 new, 2 updated, 37 unchanged)
  MOC regenerated: Claudeopedia MOC.md
  Wikilinks converted: 156
```

### Design Decisions

- **One-way sync only.** Wiki is canonical. If you edit in Obsidian, those changes are overwritten on next sync. This avoids merge conflicts entirely.
- **Title-based filenames in Obsidian.** Obsidian users expect files named by title, not slug. The slug is preserved in frontmatter for mapping back.
- **Aliases in frontmatter.** This lets Obsidian's link autocomplete find articles by multiple names.
- **MOC file.** Obsidian's graph view works better with a central MOC that links to everything.
- **`_meta/` directory.** Keeps sync machinery out of the main article folders.
- **gitignored sync state.** The `.obsidian-sync-state.json` file in knowledge-base/ is added to `.gitignore` because it contains local vault paths.

---

## Section 6: Karpathy Article Template

This is the canonical format for ALL wiki articles generated by `/wiki`, `/kb-compile`, and any other process that writes to the wiki. It is the most important part of this spec.

### Template

```markdown
---
title: "{Title — Concise, Specific, No Clickbait}"
category: {category}
tags: [{tag1}, {tag2}, {tag3}]
sources: ["{raw/category/source-file.md}"]
created: YYYY-MM-DD
updated: YYYY-MM-DD
summary: "{One sentence. What this article is about and why it matters.}"
---

# {Title}

{Opening paragraph: 3-5 sentences that establish context, state the core thesis,
and explain why this matters. The reader should know after this paragraph whether
they need to read the rest. No throat-clearing — start with the substance.}

{Body paragraphs: 3-7 paragraphs of essay-style prose. Each paragraph has a clear
topic sentence and develops one idea. Paragraphs flow logically — each one builds
on or contrasts with the previous. Dense with facts, data, and specific claims.
Every sentence carries information; no filler.

Cross-reference other wiki articles using [[slug]] syntax wherever a concept is
covered in more depth elsewhere. Example: "As documented in [[competitive-landscape-march-2026]],
the market has shifted toward..." These links create the knowledge graph.

Tables are appropriate for comparative data (feature matrices, pricing comparisons,
scoring rubrics). Use them instead of bullet lists when the data has 2+ dimensions.

Code blocks are appropriate for technical articles showing patterns, configurations,
or SQL. Use them sparingly in non-technical articles.

Specific numbers beat vague claims. "Podium charges $300-600/mo" not "Podium is expensive."
"SMS gets 3-5x higher response rates than email (Referrizer 2025)" not "SMS works better."}

## Key Concepts

{3-7 concept definitions. Each is a term or idea introduced or referenced in the article
that a reader might not know or might need a precise definition for. Not a glossary of
common terms — only concepts that are specific to this article's domain.}

- **{Concept Name}** — {1-2 sentence definition. Precise, not vague. If this concept
  has its own wiki article, link it: see [[concept-slug]].}
- **{Concept Name}** — {Definition.}
- **{Concept Name}** — {Definition.}

## Related Articles

{Links to other wiki articles that are thematically related, provide supporting evidence,
offer contrasting viewpoints, or cover prerequisite concepts. This section is the explicit
cross-reference map for this article.}

- [[{slug-1}]] — {One sentence on how it relates to this article.}
- [[{slug-2}]] — {One sentence.}
- [[{slug-3}]] — {One sentence.}

## Relevance to AgentNexLiFy

{1-2 paragraphs. What does this knowledge mean for the product, the business, or the
engineering decisions? This section transforms abstract knowledge into actionable insight.
Be specific: "This means we should prioritize X over Y" or "This validates our decision
to build Z" or "This suggests a risk we haven't accounted for in our roadmap."}
```

### Template Rules

1. **Title** — Specific and descriptive. "GoHighLevel Competitor Profile" not "Competitor Analysis." "Prompt Caching — Performance Patterns" not "Some Notes on Caching." No clickbait, no question titles, no "A Guide to X."

2. **Summary** — Exactly one sentence in the frontmatter. Must stand alone — someone scanning INDEX.md reads only this. Include the most important fact or conclusion.

3. **Opening Paragraph** — The first paragraph is the abstract. If a reader reads only this, they should understand the core claim and its significance. Start with substance, not context-setting.

4. **Body** — Essay-style prose, not bullet lists. Paragraphs, not headers-with-bullets. Tables only for genuinely tabular data. The tone is "knowledgeable colleague explaining to another knowledgeable colleague" — not tutorial, not textbook, not blog post.

5. **Key Concepts** — Not a glossary. Only concepts that are specific to this article's domain and that a reader might need defined. If a concept has its own wiki article, link it. 3-7 concepts.

6. **Related Articles** — Every article must link to at least 1 other article. The link text must explain the relationship, not just name the article. This section is manually curated (the author decides which articles are truly related), not auto-generated.

7. **Relevance to AgentNexLiFy** — Mandatory. Every article must connect back to the product. Even purely technical or academic articles must state how the knowledge applies. This is what makes the wiki a business asset rather than a personal bookmarks folder.

8. **Cross-references** — Use `[[slug]]` syntax inline wherever another article covers a topic in more depth. Don't cluster all links in Related Articles — weave them into the prose.

9. **No filler phrases.** Ban: "It's worth noting that", "Interestingly,", "It should be mentioned that", "As we can see,", "In conclusion,". Just state the thing.

10. **Numbers over adjectives.** "$300/mo" not "expensive." "3-5x higher" not "much higher." "1M context window" not "very large context."

### Example Article (Reference Quality)

```markdown
---
title: "Prompt Caching — Cost and Latency Patterns"
category: technical
tags: ["prompt-caching", "anthropic", "cost-optimization", "latency"]
sources: ["raw/technical/anthropic-prompt-caching-docs.md"]
created: 2026-04-06
updated: 2026-04-06
summary: "Anthropic's prompt caching reduces repeated-prefix costs by 90% and latency by 85%; AgentNexLiFy's widget chat is the ideal use case."
---

# Prompt Caching — Cost and Latency Patterns

Prompt caching allows reuse of previously processed prompt prefixes, avoiding
redundant computation on tokens that don't change between requests. Anthropic's
implementation (available on claude-sonnet-4-6 and claude-opus-4-6) caches the
first N tokens of a prompt and charges 1/10th the normal input price for cached
tokens on subsequent requests. For AgentNexLiFy's chat widget, where every message
in a conversation resends the full system prompt + conversation history, this
represents the single largest cost optimization available.

The mechanics are straightforward: the API hashes the prompt prefix and checks
for a cache hit. If the first 2,048+ tokens of your prompt match a cached prefix,
those tokens are served from cache at 0.1x cost and ~85% lower latency. The cache
has a 5-minute TTL that resets on each hit, meaning active conversations keep the
cache warm automatically. This aligns perfectly with chat sessions, which typically
see messages every 30-120 seconds.

The cost impact is substantial. AgentNexLiFy's widget system prompt is ~1,200
tokens. A 10-message conversation resends this prefix 10 times. Without caching,
that's 12,000 input tokens at full price. With caching, it's 1,200 at full price
(first message) plus 10,800 at 0.1x — a 82% reduction in input token cost for
that conversation. Across thousands of daily conversations, this compounds into
the difference between viable and unviable unit economics.

The latency improvement matters for perceived quality. Cached prefixes skip the
prompt processing phase entirely, reducing time-to-first-token from ~800ms to
~120ms on claude-sonnet-4-6. For a chat widget where users expect instant
responses, sub-200ms TTFT feels like the bot is "ready and waiting" rather than
"thinking." This is the kind of performance difference that affects whether a
user trusts the AI or abandons the conversation.

Implementation requires ordering the prompt so that stable content comes first:
system prompt, then business context (FAQ, business hours, service types), then
conversation history. The conversation history is the part that changes, so it
must come last. AgentNexLiFy already structures prompts this way in
`backend/services/chat_service.py`, making adoption straightforward. The only
change needed is adding `cache_control` markers to the message array, as
documented in [[claude-api-patterns]].

One caveat: caching works per-model, per-organization. If AgentNexLiFy switches
between models mid-conversation (e.g., using claude-haiku-4-5-20251001 for simple
queries and claude-sonnet-4-6 for complex ones), each model maintains a separate
cache. The routing logic in [[model-routing]] should account for this — switching
models mid-conversation loses the cache benefit.

## Key Concepts

- **Cache TTL** — Time-to-live for cached prompt prefixes. Anthropic's default is
  5 minutes, resetting on each cache hit. Active conversations keep it warm;
  abandoned ones expire naturally.
- **Prefix matching** — Caching requires the prompt prefix to match exactly,
  byte-for-byte. Any change to the system prompt (even whitespace) invalidates
  the cache for all active conversations.
- **TTFT (Time to First Token)** — The latency between sending a request and
  receiving the first token of the response. The primary user-perceived latency
  metric for streaming responses.
- **Cache-aware prompt ordering** — Structuring prompts so that stable content
  (system prompt, context) comes before variable content (conversation history,
  user message). Required for effective caching.

## Related Articles

- [[claude-api-patterns]] — Implementation details for cache_control markers in
  the Anthropic SDK.
- [[model-routing]] — How AgentNexLiFy routes between Claude models; caching
  implications for mid-conversation switches.
- [[widget-performance]] — End-to-end latency budget for the chat widget, where
  TTFT is the dominant factor.

## Relevance to AgentNexLiFy

Prompt caching should be the next cost optimization implemented. The widget chat
use case (repeated system prompt + growing conversation history) is the textbook
example of where caching delivers maximum ROI. At current volumes (~2,000
conversations/day across all tenants), the estimated monthly savings are $400-600
on API costs alone, with the TTFT improvement as a free bonus. Implementation is
a 2-hour task: add cache_control markers to the system prompt block in
chat_service.py and verify with the Anthropic usage dashboard that cache hit
rates exceed 80%.
```

---

## Section 7: Integration Map

How each new component connects to existing infrastructure:

```
                          ┌──────────────────┐
                          │   User Input      │
                          │ (URL, screenshot, │
                          │  text, file, YT)  │
                          └────────┬──────────┘
                                   │
                          ┌────────▼──────────┐
                          │    /wiki skill     │  ← NEW
                          │  (one-step ingest  │
                          │   + compile)       │
                          └──┬─────┬──────┬───┘
                             │     │      │
           ┌─────────────────┘     │      └──────────────────┐
           ▼                       ▼                          ▼
   ┌───────────────┐    ┌──────────────────┐    ┌────────────────────┐
   │ raw/{cat}/     │    │ wiki/{cat}/       │    │ Supabase           │
   │ (provenance)   │    │ (articles)        │    │ kb_articles table  │
   │                │    │                   │    │ kb_sources table   │
   └───────────────┘    └──────┬────────────┘    │ (512-dim vectors)  │
                               │                  └────────────────────┘
              ┌────────────────┼────────────────┐         ▲
              │                │                │         │
              ▼                ▼                ▼         │
   ┌──────────────┐  ┌─────────────┐  ┌──────────────┐   │
   │  INDEX.md     │  │ viewer.html  │  │ /last30days  │   │
   │  (catalog)    │  │ + data.json  │  │ (synthesis)  │   │
   │              │  │   ← NEW      │  │   ← NEW      │   │
   └──────────────┘  └─────────────┘  └──────────────┘   │
          │                                               │
          ▼                                               │
   ┌──────────────┐                              ┌────────┴───────┐
   │ /challenge-   │                              │ /kb-query      │
   │  assumptions  │ ← NEW                        │ (semantic Q&A) │
   │ (daily cron)  │                              │ (EXISTING)     │
   └──────┬────────┘                              └────────────────┘
          │                                               ▲
          ▼                                               │
   ┌──────────────┐                              ┌────────┴───────┐
   │ Appends       │                              │ embed_text()   │
   │ ## Challenges  │                              │ embed_query()  │
   │ to articles   │                              │ (Voyage AI)    │
   └──────────────┘                              │ (EXISTING)     │
                                                  └────────────────┘
          ┌──────────────┐
          │ /obsidian-    │ ← NEW
          │  sync         │
          │ (one-way      │
          │  copy to      │
          │  vault)       │──────▶  Obsidian Vault
          └──────────────┘         /Claudeopedia/
```

### Existing Infrastructure Reused

| Component | Used By | How |
|-----------|---------|-----|
| `backend/services/embeddings.py` | `/wiki`, `/kb-compile` | `embed_text()` for article vectors, `embed_query()` for search |
| `kb_articles` table (Supabase) | `/wiki`, `/last30days`, `/kb-query` | Stores articles + embeddings, queried for synthesis and search |
| `kb_sources` table (Supabase) | `/wiki` | Registers raw sources for provenance tracking |
| `INDEX.md` | All components | Article catalog, category listing, cross-reference map |
| `PENDING.md` | `/wiki` (bypasses it) | Not used by /wiki directly — /wiki marks sources as pre-compiled |
| `known-urls.json` | `/wiki` | Dedup check for URL inputs |
| `sources.yaml` | Not directly | Still used by `/kb-discover` for automated discovery |
| `scripts/daily/common.sh` | Challenge cron | `resolve_claude_binary` and other shared functions |
| `viewer-data.json` | `viewer.html` | JSON data for the browser-based viewer |

### New Files Summary

| File | Type | Size Estimate |
|------|------|---------------|
| `.claude/skills/wiki/SKILL.md` | Skill definition | ~4KB |
| `.claude/skills/last30days/SKILL.md` | Skill definition | ~3KB |
| `.claude/skills/challenge-assumptions/SKILL.md` | Skill definition | ~3KB |
| `.claude/skills/obsidian-sync/SKILL.md` | Skill definition | ~3KB |
| `knowledge-base/viewer.html` | Single-file web app | ~45KB |
| `knowledge-base/viewer-data.json` | Generated data | ~variable |
| `scripts/daily/challenge-assumptions.sh` | Cron script | ~1KB |

### CLAUDE.md Updates Needed

Add to the Skills section:
```markdown
- **Knowledge:** ... wiki, last30days, challenge-assumptions, obsidian-sync
```

Add to Workflow Commands table:
```markdown
| `/wiki` | Capture any input into a Karpathy-style wiki article (one-step ingest + compile) |
| `/last30days` | Synthesize recent knowledge into a "State of Your Mind" report |
| `/challenge-assumptions` | Generate steelman counterarguments for recent articles |
| `/obsidian-sync` | Sync wiki to Obsidian vault with wikilinks and frontmatter |
```

Add `general` to the list of wiki categories wherever categories are referenced.

### .gitignore Additions

```
knowledge-base/.obsidian-sync-state.json
```

---

## Execution Order

Build in this order. Each component is independently useful.

1. **Article template** (Section 6) — No files to create; this is a format spec referenced by everything else. Validate against existing articles to ensure compatibility.

2. **`/wiki` skill** (Section 1) — The core input mechanism. Once this works, every subsequent component has articles to work with.

3. **Viewer data generator** (the Python script in Section 3) — Needed by the viewer but also useful standalone for validating INDEX.md consistency.

4. **`viewer.html`** (Section 3) — Immediate visual payoff. Makes the wiki tangible.

5. **`/last30days` skill** (Section 2) — Synthesis layer. Only useful once there are enough articles to synthesize.

6. **Challenge cron** (Section 4) — Runs against existing articles. Can be added at any time.

7. **Obsidian sync** (Section 5) — Optional. Only needed if using Obsidian.

---

## Success Criteria

The system is working when:

1. `/wiki https://some-article.com` produces a wiki article, updates INDEX.md, stores an embedding in Supabase, and the article appears in `viewer.html` after a page refresh.
2. `/wiki /tmp/screenshot.png` reads the screenshot, extracts knowledge, and produces the same output chain.
3. `/last30days` produces a synthesis report that surfaces non-obvious connections between articles.
4. The viewer loads in under 1 second and all filters (search, category, tag, date) work.
5. After the challenge cron runs, every recent article has a `## Challenges` section with specific, steelmanned counterarguments.
6. `/obsidian-sync /path/to/vault` produces a valid Obsidian vault with working `[[wikilinks]]` between articles.
7. `/kb-query` still works and finds articles created by `/wiki` (because they share the same embedding + storage infrastructure).
