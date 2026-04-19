---
name: source-validation
description: Score credibility, bias, and relevance of a source before it enters the knowledge base. Use when running `/kb-ingest`, `/kb-discover`, or before promoting raw sources to wiki via `/kb-compile`. Prevents low-quality or biased content from polluting tenant KBs.
version: 1.0.0
origin: claude
user-invocable: true
triggers:
- validate source
- source validation
- check credibility
- score source
- trust score
effort: low
---

# Source Validation — Credibility Gate for KB Pipeline

Pre-compile filter that scores every raw source on 3 axes before it reaches `knowledge-base/wiki/`. Prevents LLM slop, SEO farms, and vendor PR from contaminating tenant-facing answers.

## When to Use
- Before `/kb-compile` promotes raw → wiki
- Inside `/kb-ingest` after fetching URL
- Inside `/kb-discover` before scoring relevance
- When user asks "is this source trustworthy?"

## When NOT to Use
- First-party AgentNexLiFy docs (trust = 10 by definition)
- Official vendor docs on product pages (trust = 9)
- Already-validated wiki articles
- Anonymous tips / user-submitted chat messages (never enter KB)

## Scoring Rubric (0-10 scale)

### Reliability (weight 0.5)
- 10 — peer-reviewed research, official gov/standards body, Anthropic/OpenAI/Google first-party docs
- 8 — Tier-1 tech media (TechCrunch, The Verge, Ars), established analyst firms (Gartner, Forrester)
- 6 — Recognized company engineering blogs (Vercel, Stripe, Supabase), YC-backed founder posts
- 4 — Personal blogs with track record, Substack analysts, Hacker News top-commenters
- 2 — Medium/dev.to posts without author credentials, anonymous forum threads
- 0 — Unattributed, obvious LLM-generated content, content farms

### Bias (weight 0.3)
- 10 — Neutral technical explainer, no product promotion, no affiliate links
- 7 — Discloses sponsor / affiliation, discusses tradeoffs fairly
- 4 — Clear vendor PR but technically accurate
- 2 — Heavy sales pitch disguised as analysis
- 0 — Paid placement, undisclosed affiliate, competitor hit piece

### Relevance (weight 0.2)
- 10 — Direct match to AgentNexLiFy category (competitors, ai-llm, small-biz-saas, verticals, technical, regulations, growth)
- 7 — Adjacent topic that informs decisions
- 4 — Tangential — only useful as background
- 0 — Off-topic

## Composite Trust Score
```
trust_score = (reliability * 0.5) + (bias * 0.3) + (relevance * 0.2)
```

## Action Thresholds
| Score | Action |
|-------|--------|
| 8.0+ | Auto-promote to wiki on next `/kb-compile` |
| 6.0-7.9 | Compile with `caveat: "single-source claim"` frontmatter |
| 4.0-5.9 | Stay in `raw/`, require corroborating source before promotion |
| <4.0 | Reject — delete from `raw/`, add URL to `knowledge-base/blocked-urls.json` |

## Workflow

### Step 1: Read Input
Accept URL or path to `knowledge-base/raw/{category}/{file}.md`.

### Step 2: Extract Signals
- Author name + bio + publication date
- Domain TLD + Whois age (use WebFetch if URL)
- Outbound links (affiliate? tracking params?)
- Citation density (references per 1000 words)
- Hedging ratio ("might", "could", "possibly" per 1000 words)
- First-person promotion ratio

### Step 3: Apply Rubric
Score each axis 0-10 with 1-sentence justification. Compute composite.

### Step 4: Write Frontmatter
Update raw file's YAML:
```yaml
---
title: "..."
source_url: "..."
discovered: YYYY-MM-DD
category: ...
relevance_score: 8   # existing field
trust_score: 7.4     # new — this skill's output
reliability: 8
bias: 7
validation_notes: "Author is Supabase engineer; product mentioned but tradeoffs acknowledged."
validated_at: YYYY-MM-DD
---
```

### Step 5: Act on Threshold
- 8.0+ → no-op (auto-compile)
- 6.0-7.9 → append caveat to frontmatter
- 4.0-5.9 → move to `knowledge-base/raw/_quarantine/`
- <4.0 → delete file + add to blocked-urls.json

### Step 6: Report
One-line output:
```
Validated: {title} → trust {score}/10 ({action}).
```

## Anti-patterns
- Never validate a source without reading it (no trust-by-URL-pattern)
- Never promote a sub-4.0 source because "it's the only one"
- Never score relevance in isolation — context of AgentNexLiFy verticals matters
- Never skip validation on competitor content (highest bias risk)

## Cross-refs
- `.claude/skills/kb-ingest/SKILL.md` — upstream
- `.claude/skills/kb-compile/SKILL.md` — downstream consumer
- `.claude/skills/kb-discover/SKILL.md` — invokes this on each found URL
- `knowledge-base/INDEX.md` — category taxonomy
- `.claude/rules/kb-first.md` — KB-first principle
