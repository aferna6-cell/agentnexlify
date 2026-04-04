---
name: kb-health
description: "Audit the knowledge base for staleness, gaps, contradictions, and missing cross-links. Reports health score and suggests improvements."
user_invocable: true
---

# KB Health — Wiki Audit

Run quality checks across the knowledge base and suggest improvements.

## Usage

- `/kb-health` — full audit
- `/kb-health --category competitors` — audit one category

## Checks

### 1. Staleness Check

For each wiki article, check if ALL sources are older than 60 days:

```sql
SELECT slug, title, category, updated_at,
       now() - updated_at AS age
FROM kb_articles
ORDER BY updated_at ASC;
```

Flag articles where `age > 60 days` as stale.

For stale articles, suggest discovery queries that could refresh them. Example:
- `wiki/competitors/gohighlevel.md` is 75 days old → suggest searching "GoHighLevel updates April 2026"

### 2. Category Coverage

Count articles per category:

```sql
SELECT category, COUNT(*) as count, SUM(word_count) as total_words
FROM kb_articles
GROUP BY category
ORDER BY count;
```

Flag categories with fewer than 3 articles as "thin coverage."

Compare against the 7 expected categories and flag any with 0 articles.

### 3. Missing Cross-Links

For each article, read its content and check for mentions of entities/concepts that have their own wiki articles but aren't linked with `[[backlink]]` syntax.

Example: if `wiki/competitors/gohighlevel.md` mentions "prompt caching" and `wiki/technical/prompt-caching.md` exists, but there's no `[[prompt-caching]]` link, flag it.

### 4. Orphan Detection

Find articles that are never referenced by any other article (no incoming backlinks). These might be isolated or poorly integrated.

### 5. Contradiction Check

Read articles within the same category and check for conflicting claims. Example:
- Article A says "GoHighLevel charges $97/mo for base plan"
- Article B says "GoHighLevel starts at $127/mo"
- Flag: "Possible contradiction about GHL pricing between [[gohighlevel]] and [[competitor-pricing-2026]]"

### 6. Embedding Coverage

```sql
SELECT COUNT(*) as total,
       COUNT(embedding) as has_embedding,
       COUNT(*) - COUNT(embedding) as missing_embedding
FROM kb_articles;
```

Flag articles missing embeddings — they won't appear in semantic search.

### 7. Pending Source Check

```sql
SELECT COUNT(*) FROM kb_sources WHERE compiled = false;
```

Report uncompiled sources.

## Health Report

Output a structured report:

```markdown
## Knowledge Base Health Report — YYYY-MM-DD

### Score: 78/100

### Summary
- Total articles: 42
- Total words: ~85,000
- Pending sources: 3
- Missing embeddings: 1

### Staleness (15 points deducted)
- 🔴 `wiki/competitors/phonely.md` — 90 days old
- 🟡 `wiki/regulations/hipaa.md` — 65 days old
- Suggested refresh queries:
  - "Phonely AI receptionist 2026 update"
  - "HIPAA AI chatbot compliance 2026"

### Coverage
| Category | Articles | Words | Status |
|----------|----------|-------|--------|
| competitors | 8 | 12,000 | ✅ Good |
| ai-llm | 12 | 18,000 | ✅ Good |
| regulations | 2 | 3,000 | ⚠️ Thin |
| growth | 1 | 1,500 | 🔴 Gap |

### Missing Cross-Links (5 points deducted)
- `gohighlevel.md` mentions "AI Employee" but doesn't link to [[ai-employee-market]]
- `prompt-caching.md` mentions "Claude" but doesn't link to [[claude-sonnet-4-6]]

### Contradictions (2 points deducted)
- GHL pricing conflict between [[gohighlevel]] and [[competitor-pricing-2026]]

### Recommended Actions
1. Run `/kb-discover regulations growth` to fill coverage gaps
2. Run `/kb-compile` to process 3 pending sources
3. Review pricing contradiction in competitor articles
```

### Scoring

| Check | Max Points | Deduction Logic |
|-------|-----------|-----------------|
| No stale articles | 25 | -5 per stale article (cap -25) |
| All categories ≥ 3 articles | 20 | -5 per thin category (cap -20) |
| No missing cross-links | 15 | -1 per missing link (cap -15) |
| No contradictions | 15 | -3 per contradiction (cap -15) |
| All embeddings present | 10 | -2 per missing (cap -10) |
| No pending sources | 10 | -2 per pending (cap -10) |
| No orphan articles | 5 | -1 per orphan (cap -5) |
