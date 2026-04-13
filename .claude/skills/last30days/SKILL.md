---
name: last30days
description: Synthesize recent knowledge accumulation into a 'State of Your Mind' report by grouping by theme, identifying patterns, and surfacing blind spots. Use when user says 'last30days', 'state of your mind', 'knowledge synthesis', '30 day report', 'weekly review', 'bi-weekly review', or asks about last30days.
version: 1.0.0
origin: claude
user-invocable: true
triggers:
- last30days
- state of your mind
- knowledge synthesis
- 30 day report
- weekly review
- bi-weekly review
effort: medium
---

# `/last30days` Skill — Claudeopedia Knowledge Synthesis

**Purpose:** Synthesize the past 30 days of knowledge accumulation into a structured "State of Your Mind" report. Answers: What have I been learning? What patterns are emerging? What am I ignoring?

**Infrastructure:** Reads from `knowledge-base/wiki/`, `knowledge-base/INDEX.md`, and queries the `kb_articles` table in Supabase. Saves output to `knowledge-base/_outputs/`.

---

## Usage

```
/last30days                          # standard 30-day report
/last30days --compare 2026-03-01     # compare current 30 days vs 30 days ending at given date
/last30days --days 14                # override window to 14 days (e.g. for bi-weekly review)
/last30days --days 7                 # weekly review mode
```

## When to Use
- Synthesizing recent knowledge base activity into a structured report
- Identifying emerging patterns across wiki articles
- Comparing knowledge accumulation between two time windows

## When NOT to Use
- Checking knowledge base health (use kb-health instead)
- Adding or compiling articles (use wiki, kb-ingest, or kb-compile instead)
- Querying specific facts from the knowledge base (use kb-query instead)

## Full Workflow (6 Steps)

### Step 1: Identify Recent Articles

Read `knowledge-base/INDEX.md` to get the full article catalog.

For each article listed, read its frontmatter to extract `created` and `updated` dates.

Filter to articles where `created` OR `updated` falls within the target window:
- Default window: last 30 days from today
- If `--days N` flag: last N days from today
- If `--compare DATE`: also load a second window of 30 days ending at DATE (used in Step 4)

Also query Supabase for completeness and to catch any articles stored in the DB but not yet reflected in INDEX.md:

```sql
SELECT slug, title, category, tags, summary, word_count, updated_at
FROM kb_articles
WHERE updated_at >= now() - interval '30 days'
ORDER BY updated_at DESC;
```

Merge the two lists (INDEX.md scan + Supabase query) by slug, deduplicating. The article file on disk is authoritative for content; Supabase provides metadata.

If no articles fall within the window, output:
```
No articles found in the last {N} days.
Run /wiki to start capturing knowledge, or /kb-discover to find relevant articles automatically.
```
and stop.

### Step 2: Read All Matching Articles

For each article identified in Step 1, read the full content from `knowledge-base/wiki/{category}/{slug}.md`.

Do not read just the summaries — full article content is required for quality synthesis. This costs more tokens but produces dramatically better output.

Track for each article:
- Title, category, slug
- Created date, updated date
- Word count
- Tags
- Full body text (for synthesis in Step 3)

### Step 3: Analyze and Synthesize

Generate a structured analysis with all 8 sections below. The sections are ordered by value, not chronology.

---

#### Section 1: Overview

A brief quantitative summary of the window:
- Total articles created or updated
- Total word count analyzed
- Categories active (with article counts per category)
- Date range of the window
- Most recent article (title + date)

Format example:
```
## Overview

30-day window: 2026-03-07 to 2026-04-06
Articles analyzed: 14 (9 new, 5 updated)
Total words: 18,400
Categories active: 5 of 8 (competitors: 4, ai-llm: 4, technical: 3, growth: 2, verticals: 1)
Most recent: "Toma AI — Receptionist Vertical" (2026-04-05)
```

---

#### Section 2: By Category

For each category that has at least one article in the window, write a 2-3 sentence prose summary of what was learned in that category. Include article count and total words.

Do not write a section for categories with zero activity.

Format: one H3 per active category, with article list and summary paragraph.

Example:
```
### Competitors (4 articles, 5,200 words)
[article titles as bullet list]

The window covered three AI-native competitors (Toma, Phonely, Drillbit) and an
updated GoHighLevel profile. The dominant theme is vertical specialization:
all three new entrants target narrow industries (contractors, calls, receptionist)
rather than the horizontal SMB market. GoHighLevel remains the horizontal default
at $97-$497/mo; the vertical entrants charge $200-$800/mo for narrower scope but
higher automation depth.
```

---

#### Section 3: Top Concepts Learned

The 5-10 most significant new ideas, techniques, facts, or frameworks encountered in the window. These are the "highest density" insights — things that changed or expanded understanding in a meaningful way.

For each concept:
- A bold title (the concept name)
- 2-3 sentences explaining what it is and why it matters
- Article citations in `[[slug]]` format

Criteria for "top concept": new to the knowledge base, non-obvious, actionable, or paradigm-shifting. Don't list facts that were already known.

Format:
```
### Top Concepts Learned

1. **Concept Name.** Explanation of what this is and why it matters for AgentNexLiFy.
   Source: [[article-slug]].

2. **Concept Name.** Explanation...
   Source: [[article-slug]], [[article-slug-2]].
```

---

#### Section 4: Surprising Insights

Things that contradicted prior assumptions, unexpected connections between articles, or non-obvious implications. These are the most valuable part of the report — they indicate genuine learning rather than confirmation of existing beliefs.

For each surprising insight:
- State what was surprising ("Expected X, found Y")
- Cite the specific article(s) that surfaced this
- State one implication for AgentNexLiFy

If nothing in the window was genuinely surprising, say so explicitly: "No significant surprises this window. The articles largely confirmed existing assumptions." This is honest and provides a data point about the diversity of sources being consumed.

---

#### Section 5: Belief Changes

Explicit statements of "I used to think X, now I think Y" based on evidence from the articles in this window.

Format for each belief change:
```
**[Topic]** Previously: {old belief}. Now: {new belief}. Evidence: [[slug]].
```

If no belief changes are evident in this window, say:
> No explicit belief changes this window. This may indicate the articles were confirmatory rather than challenging, or that the window was too short to accumulate enough evidence.

Including this section even when empty trains the habit of noticing when understanding shifts. Do not skip it.

---

#### Section 6: Knowledge Gaps

Topics that were touched superficially but not explored deeply. Categories with zero or thin coverage. Questions raised by the window's articles that weren't answered by other articles. Concepts that appeared in multiple articles but have no dedicated wiki article.

Sub-sections:
1. **Thin Coverage** — Categories with 0 articles in this window, or categories with 1 article that felt underexplored given its importance.
2. **Unanswered Questions** — Specific questions raised by articles in this window that the knowledge base cannot currently answer. List as questions, not statements.
3. **Missing Articles** — Concepts referenced in `[[slug]]` notation within articles that don't correspond to any existing wiki article. These are explicit gaps in the knowledge graph.

Format:
```
### Knowledge Gaps

**Thin Coverage:** `regulations` had zero activity this window despite TCPA exposure
being a live risk for the SMS automation features.

**Unanswered Questions:**
- What is Toma's actual pricing structure? The profile mentions "usage-based" but lacks numbers.
- How does GoHighLevel's AI Employee handle multi-location tenants?

**Missing Articles:**
- [[ai-receptionist-market]] — referenced in 3 articles, no article exists
- [[tcpa-sms-compliance]] — referenced in automations context, no article exists
```

---

#### Section 7: Emerging Themes

Patterns that span multiple categories or articles. Cross-cutting threads that no single article captured but become visible when viewing the window as a whole.

For each theme:
- Name it concisely
- Explain which articles it spans (with `[[slug]]` citations)
- State the implication: "This pattern suggests..."

A theme is only worth noting if it spans at least 2 articles in different categories. Single-category patterns are captured in Section 2.

Example:
```
### Emerging Themes

**Vertical specialization is the winning wedge.** Three separate competitor articles
([[toma-ai-receptionist]], [[drillbit-contractor-platform]], [[phonely-profile]])
all describe companies that started with a narrow vertical before expanding.
This pattern suggests the horizontal-first approach (target all SMBs) faces more
competition than the vertical-first approach (win contractors, then expand).
AgentNexLiFy's verticals feature set may be its most defensible moat.

**Cost pressure is accelerating model switching.** Two technical articles
([[prompt-caching-patterns]], [[model-routing-strategies]]) and one competitor
profile ([[gohighlevel-q1-2026]]) all touch on cost per conversation as a key metric.
Inference costs are falling faster than most pricing models assumed.
```

---

#### Section 8: Recommendations

3-5 specific, actionable recommendations based on the analysis. Each recommendation should map to a concrete next step.

Types of recommendations:
- **Research:** "Run /wiki on [specific URL] to fill the [topic] gap"
- **Write:** "Write a new article on [topic] — it was referenced 3x but doesn't exist"
- **Deepen:** "[[existing-article]] is thin — find 2 more sources and update it"
- **Challenge:** "Run /challenge-assumptions on [[article]] — its core claim about X seems testable"
- **Query:** "Run /kb-query 'question' — these articles together might answer it"
- **Act:** "Based on [[article]], consider [specific product/engineering action]"

Format each recommendation as a numbered item with enough context to act on it immediately.

---

### Step 4: Comparison Mode (if `--compare` flag)

If a comparison date was provided:

1. Load articles from the comparison window: 30 days ending at the provided DATE (not a variable window — fixed 30 days for apples-to-apples comparison).

2. Run the same 8-section analysis for the comparison window, but abbreviated (1 paragraph per section rather than full analysis).

3. Add a **Delta** section after Section 8 that explicitly compares the two windows:

```
## Delta: {current_window_end} vs {comparison_date}

**New categories explored:** [categories active now that were dormant in comparison window]
**Categories gone dormant:** [categories active in comparison window, silent now]
**Concept velocity:** {articles/week now} vs {articles/week then} ({+/- change}%)
**Theme evolution:** What was trending in the comparison window vs now
**Belief trajectory:** Any beliefs that changed once (comparison window) and changed again (now)
```

The comparison window data is not saved separately — only the current window report is saved to disk.

### Step 5: Save Report

Create the `knowledge-base/_outputs/` directory if it doesn't exist.

Write the full report to:
```
knowledge-base/_outputs/YYYY-MM-DD-last30days.md
```

With this frontmatter:
```yaml
---
title: "State of Your Mind — YYYY-MM-DD"
type: synthesis
window_start: YYYY-MM-DD
window_end: YYYY-MM-DD
articles_analyzed: N
total_words_analyzed: N
categories_active: N
compared_to: YYYY-MM-DD  # only if --compare was used, omit otherwise
created: YYYY-MM-DD
---
```

The file should contain the full report as generated in Step 3 (and Step 4 if comparison mode).

### Step 6: Report

Display the full report in the terminal.

Then output the summary footer:
```
Report saved to: knowledge-base/_outputs/YYYY-MM-DD-last30days.md
Window: {window_start} to {window_end} | Articles: {N} | Words: {N}
Active categories: {list}
```

---

## Design Decisions

- The report reads **full article content**, not just summaries. This costs more tokens but produces dramatically better synthesis. The summaries are one sentence each; the full articles contain the nuance and evidence needed for Sections 3-7.
- **"Belief Changes" is included even when empty.** Its presence as a required section trains the habit of noticing when understanding shifts. Omitting it when empty would train the opposite habit.
- **Comparison mode uses a fixed 30-day window ending at the provided date**, not a variable window. This keeps comparisons apples-to-apples. "Last 30 days before March 1st" vs "last 30 days before April 6th" are directly comparable.
- **Reports are saved to `_outputs/`** — the same directory used by `/kb-query` outputs — rather than a new directory. This keeps all synthesis artifacts co-located.
- **The 8 sections are ordered by value, not by workflow.** Overview first (orientation), then category breakdown, then the high-value synthesis sections (surprising insights, belief changes, themes), then actionable output (recommendations). Do not reorder them.
- **Unanswered questions are surfaced explicitly.** Most synthesis tools only report what was learned. Listing what wasn't answered is equally valuable and harder to do without explicit structure.

---

## Output Structure Reference

The final report structure (for quick reference when writing the output):

```
---
[YAML frontmatter]
---

## Overview
[Quantitative summary: N articles, N words, categories, date range]

## By Category
### {Category Name} ({N} articles, {N} words)
[Bullet list of article titles]
[2-3 sentence prose summary of what was learned]
... (one H3 per active category, skip inactive)

## Top Concepts Learned
1. **Concept.** 2-3 sentence explanation. Source: [[slug]].
... (5-10 items, only genuinely new/significant concepts)

## Surprising Insights
[Specific contradictions, unexpected connections, non-obvious implications]
[Or: "No significant surprises this window. {reason}."]

## Belief Changes
**[Topic]** Previously: X. Now: Y. Evidence: [[slug]].
... (or explicit statement that no belief changes were found)

## Knowledge Gaps
**Thin Coverage:** ...
**Unanswered Questions:**
- Question 1?
- Question 2?
**Missing Articles:**
- [[slug]] — referenced N times, no article exists

## Emerging Themes
**Theme Name.** [Cross-category pattern + implication for AgentNexLiFy]
... (only themes spanning 2+ articles in different categories)

## Recommendations
1. [Specific action with enough context to execute immediately]
2. [Specific action]
... (3-5 items)

## Delta: {current} vs {comparison}  [only if --compare flag was used]
**New categories explored:** ...
**Categories gone dormant:** ...
**Concept velocity:** N/week now vs M/week then
**Theme evolution:** ...
**Belief trajectory:** ...
```
