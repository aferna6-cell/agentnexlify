---
name: wiki
description: "Capture any input (screenshot, URL, text, file, YouTube) into a Karpathy-style wiki article. One-step raw-to-wiki."
user_invocable: true
---

# `/wiki` Skill — Claudeopedia Fast Ingest

**Purpose:** One-command ingestion of ANY input into a structured wiki article. Unlike `/kb-ingest` (which saves raw and defers to `/kb-compile`), `/wiki` goes raw-to-wiki in a single invocation. It is the "fast path" for capturing knowledge.

**Infrastructure:** Uses `backend/services/embeddings.py` (Voyage AI, voyage-3-lite, 512-dim), `kb_articles` table in Supabase, and `knowledge-base/INDEX.md` as the catalog.

---

## Usage

```
/wiki <input> [category]
```

Where `<input>` is one of:
- A screenshot path: `/wiki /tmp/screenshot.png`
- A URL: `/wiki https://arxiv.org/abs/2401.12345`
- A YouTube URL: `/wiki https://youtube.com/watch?v=abc123`
- Raw text (quoted): `/wiki "Transformers use self-attention to..."`
- A file path: `/wiki ./notes/meeting-notes.md`
- No argument: `/wiki` then paste content when prompted

And `[category]` is optional (auto-detected if omitted):
- `competitors`, `ai-llm`, `small-biz-saas`, `verticals`, `technical`, `regulations`, `growth`, `general`

---

## Full Workflow (11 Steps)

### Step 1: Detect Input Type

Parse the argument to determine input type:

| Pattern | Input Type |
|---------|------------|
| Starts with `http://` or `https://` AND contains `youtube.com` or `youtu.be` | YouTube |
| Starts with `http://` or `https://` | URL |
| Ends with `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp` | Screenshot |
| Valid file path that exists on disk | File |
| No argument provided | Prompt |
| Everything else | Raw text |

If no argument: prompt the user to paste their text, then treat the pasted content as Raw text.

### Step 2: Extract Content

Based on the detected input type:

| Type | Extraction Method |
|------|-------------------|
| **Screenshot** | Use the Read tool to read the image file. Claude extracts all visible text, diagrams, code, tables, and contextual information from the image. Capture everything visible, including UI labels, chart data, code snippets, and any overlaid text. |
| **URL** | Use WebFetch to retrieve page content. Strip navigation, ads, sidebars, footers. Extract: title, body text, publication date, author if present. |
| **YouTube** | Use WebFetch on the YouTube URL. Extract: video title, channel name, description. If transcript data is embedded in the page content, extract it. If no transcript is available, note `transcript_unavailable: true` in frontmatter and work from title + description + comments if visible. |
| **File** | Use the Read tool to read the file. Preserve any existing structure. Support: `.md`, `.txt`, `.py`, `.js`, `.ts`, `.json`, `.yaml`, `.html`, `.pdf` (first 2000 lines). |
| **Raw text** | Use the text directly as provided. |

### Step 3: Determine Category

If a category was passed as an argument, use it and skip detection.

If not provided, analyze the extracted content and assign to one of these 8 categories:

| Category | Content Signals |
|----------|-----------------|
| `competitors` | About specific competitor companies, market positioning, feature comparisons, pricing, customer reviews of competitors |
| `ai-llm` | About AI models, LLM capabilities, prompt engineering, agent architectures, context windows, fine-tuning, embeddings, eval frameworks |
| `small-biz-saas` | About SaaS business models, pricing strategy, churn, PLG, onboarding, retention, SMB-specific dynamics |
| `verticals` | About specific industries: contractors, dental, salon, legal, restaurant, real estate, fitness, healthcare, automotive |
| `technical` | About software engineering patterns, database design, embeddings, streaming, infrastructure, security, performance optimization |
| `regulations` | About compliance (HIPAA, TCPA, GDPR, CCPA), data privacy, AI disclosure laws, opt-out requirements, telemarketing law |
| `growth` | About distribution, virality, SEO, GEO, partnerships, marketing, content strategy, paid acquisition, PLG motions |
| `general` | Personal learning, research, concepts, and ideas that don't fit the above taxonomy |

Assign the single best-fit category. When a piece of content could fit two categories, pick the more specific one (e.g., `competitors` over `small-biz-saas` for a GoHighLevel pricing analysis).

### Step 4: Check for Existing Article

Read `knowledge-base/INDEX.md` to see the full article catalog.

Decision logic:
- If an existing article covers the **same entity** (e.g., you're ingesting new information about GoHighLevel and `gohighlevel.md` already exists) → **merge** into the existing article: update content, add new information as an additional section or inline, bump the `updated` date, append to `sources`.
- If the input covers a **new concept or entity** → **create** a new article.
- If **uncertain** → **create** a new article. Two focused articles are better than one corrupted merged article.

When merging: read the existing article first, then synthesize new information into it. Don't append raw blocks — integrate naturally into the prose.

### Step 5: Generate Article

Using the extracted content as source material, write a wiki article following the **Karpathy Article Template** (reproduced verbatim below in the Template Reference section).

Key principles for article generation:
- **Dense, not fluffy.** Every sentence must contain information. No filler, no throat-clearing.
- **Essay-style, not listicle.** Flowing paragraphs, not bullet-point dumps. Tables only for genuinely tabular data (feature matrices, pricing comparisons).
- **Opinionated where warranted.** "This matters because X" not just "This exists."
- **Cross-linked.** Reference existing wiki articles using `[[slug]]` syntax wherever relevant. Read INDEX.md to know what slugs exist. Weave links into prose, not just in Related Articles.
- **Source-attributed.** Specific claims should cite where they came from (article title, URL, or date).
- **Numbers over adjectives.** "$300/mo" not "expensive." "3-5x higher response rates" not "much better." "1M context window" not "very large."

### Step 6: Save Article

Generate the slug from the title:
- Lowercase
- Replace spaces and special characters with hyphens
- Remove any characters that aren't alphanumeric or hyphens
- Max 60 characters
- Example: "GoHighLevel — AI Employee Feature" → `gohighlevel-ai-employee-feature`

Write the article to:
```
knowledge-base/wiki/{category}/{slug}.md
```

Also save the raw source to `knowledge-base/raw/{category}/{slug}-raw.md` with this frontmatter:
```yaml
---
title: "Original Source Title"
source_url: https://...   # or "screenshot", "clipboard", "local:{path}"
discovered: YYYY-MM-DD
category: {category}
relevance_score: 8
ingested_via: wiki
---
```
Followed by the raw extracted content (unprocessed).

### Step 7: Generate Embedding

Run Python to generate the embedding using the project's embeddings service:

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

Capture the printed output — it is the 512-dimensional vector string needed for Step 8.

### Step 8: Store in Supabase

Upsert into `kb_articles` via Supabase MCP:

```sql
INSERT INTO kb_articles (slug, title, category, summary, content, embedding, source_urls, tags, word_count, updated_at)
VALUES (
    '{category}/{slug}',
    '{title}',
    '{category}',
    '{one-line summary from frontmatter}',
    '{full markdown content of the article}',
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
VALUES (
    '{source_url_or_type}',
    'raw/{category}/{slug}-raw.md',
    '{category}',
    8,
    '{title}',
    now(),
    true,
    now()
)
ON CONFLICT (source_url) DO NOTHING;
```

### Step 9: Update INDEX.md

Read the current `knowledge-base/INDEX.md`. Add or update the entry under the appropriate category section:

```markdown
- [{title}](wiki/{category}/{slug}.md) — {one-line summary}. Tags: {tag1}, {tag2}
```

Update the statistics at the top of INDEX.md:
- Increment total articles count (if new article)
- Update "Last compiled" date to today

Rebuild the Cross-Reference Map by scanning for all `[[slug]]` references across all wiki articles and listing them.

After updating INDEX.md, regenerate `knowledge-base/viewer-data.json` with this Python script:

```python
import json, re, os
from pathlib import Path
try:
    import yaml
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "pyyaml", "--break-system-packages", "-q"])
    import yaml

kb = Path('knowledge-base')
articles = []
tag_freq = {}
cat_counts = {}

for md_file in sorted(kb.glob('wiki/**/*.md')):
    if '_outputs' in str(md_file):
        continue
    text = md_file.read_text()
    if not text.startswith('---'):
        continue
    parts = text.split('---', 2)
    if len(parts) < 3:
        continue
    _, fm_str, body = parts
    try:
        meta = yaml.safe_load(fm_str)
    except Exception:
        continue
    if not meta:
        continue

    slug = f'{md_file.parent.name}/{md_file.stem}'
    tags = meta.get('tags', []) or []
    cat = meta.get('category', md_file.parent.name)

    for t in tags:
        tag_freq[t] = tag_freq.get(t, 0) + 1
    cat_counts[cat] = cat_counts.get(cat, 0) + 1
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
import datetime
data = {
    'generated': datetime.datetime.utcnow().isoformat() + 'Z',
    'stats': {
        'total_articles': len(articles),
        'total_words': sum(a['word_count'] for a in articles),
        'categories': len(cat_counts),
        'last_updated': str(datetime.date.today())
    },
    'articles': articles,
    'categories': [
        {'name': c, 'color': colors.get(c, '#6b7280'), 'count': n}
        for c, n in sorted(cat_counts.items())
    ],
    'tag_frequencies': tag_freq
}
(kb / 'viewer-data.json').write_text(json.dumps(data, indent=2))
print(f'viewer-data.json: {len(articles)} articles, {sum(a["word_count"] for a in articles)} words')
```

### Step 10: Update known-urls.json

If the input was a URL (not a screenshot, file, or raw text), append it to `knowledge-base/known-urls.json`.

Read the existing file (or start with `[]` if it doesn't exist), add the new URL if not already present, and write back.

### Step 11: Report

Output the result in this format:

```
Wiki: **{title}** → wiki/{category}/{slug}.md
  Category: {category} | Words: {word_count} | Tags: {tag1}, {tag2}, {tag3}
  Embedding: stored ({similarity score to nearest existing article, e.g. "0.87 similar to gohighlevel.md"})
  Cross-links: [[article1]], [[article2]]
  Action: {created | merged into existing slug}
```

If the embedding Python script fails (missing deps, etc.), note the failure but continue — the article file and INDEX.md are the primary artifacts.

---

## Design Decisions

- `/wiki` bypasses the two-step raw-then-compile flow of `/kb-ingest` + `/kb-compile`. It does both in one invocation. The raw file is still saved to `raw/` for provenance, but it is immediately marked as `compiled: true`.
- Screenshots are first-class inputs. Claude reads the image directly and extracts structured knowledge. This handles Twitter/X threads, diagrams, whiteboard photos, conference slide photos, and paper figures.
- YouTube URLs attempt transcript extraction from the page content. If no transcript is found, the article is generated from video metadata and flagged `transcript_unavailable: true` in frontmatter. A partial article with that flag is better than no article.
- The merge-vs-create decision defaults to **create**. Two related articles can be merged later intentionally; a corrupted merge is difficult to recover from.
- The `general` category exists for personal learning, concepts, and knowledge that doesn't map to the 7 existing categories. It is intentionally broad.

---

## Template Reference (VERBATIM — Karpathy Article Format)

Every article produced by `/wiki` must follow this template exactly. Do not deviate.

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

### Template Rules (Hard Constraints)

1. **Title** — Specific and descriptive. "GoHighLevel Competitor Profile" not "Competitor Analysis." No clickbait, no question titles, no "A Guide to X." No "Notes on X."

2. **Summary** — Exactly one sentence in the frontmatter. Must stand alone — someone scanning INDEX.md reads only this. Must include the most important fact or conclusion, not a topic description.

3. **Opening Paragraph** — The first paragraph is the abstract. If a reader reads only this, they should understand the core claim and its significance. Start with substance.

4. **Body** — Essay-style prose, not bullet lists. Paragraphs, not headers-with-bullets. Tables only for genuinely tabular data. Tone: "knowledgeable colleague explaining to another knowledgeable colleague."

5. **Key Concepts** — Not a general glossary. Only concepts specific to this article's domain that a reader might need defined. 3-7 concepts. Link to existing articles where applicable.

6. **Related Articles** — Every article must link to at least 1 other article. The link text must explain the relationship, not just name the article.

7. **Relevance to AgentNexLiFy** — Mandatory in every article. Even purely academic articles must state how the knowledge applies to the product or business decisions.

8. **Cross-references** — Use `[[slug]]` syntax inline throughout the body prose wherever another article covers a topic in more depth. Don't cluster all links in Related Articles.

9. **No filler phrases.** Banned: "It's worth noting that", "Interestingly,", "It should be mentioned that", "As we can see,", "In conclusion,". State the thing directly.

10. **Numbers over adjectives.** "$300/mo" not "expensive." "3-5x higher" not "much higher." Cite sources for statistics when available.

---

## Example Article (Reference Quality)

The following article demonstrates the correct output format and prose quality. Use it as a benchmark.

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
