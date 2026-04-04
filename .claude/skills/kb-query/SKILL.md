---
name: kb-query
description: "Ask questions against the knowledge base using semantic search. Embeds your question, finds relevant articles via pgvector cosine similarity, and synthesizes an answer."
user_invocable: true
---

# KB Query — Semantic Q&A

Ask natural language questions against the compiled knowledge base.

## Usage

- `/kb-query How does GoHighLevel's AI Employee compare to our chat widget?`
- `/kb-query What are the latest LLM context window improvements?`
- `/kb-query What compliance risks do we face with SMS automation?`

## Workflow

### Step 1: Embed the Question

Run Python to embed the query using the query-optimized endpoint:

```python
import asyncio
import sys
sys.path.insert(0, '.')
from backend.services.embeddings import embed_query

question = "USER QUESTION HERE"
embedding = asyncio.run(embed_query(question))
# Format as string for SQL
embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
print(embedding_str)
```

### Step 2: Semantic Search

Query Supabase for the top 10 most similar articles:

```sql
SELECT slug, title, category, summary, content, tags,
       1 - (embedding <=> 'EMBEDDING_VECTOR'::vector) AS similarity
FROM kb_articles
WHERE embedding IS NOT NULL
ORDER BY embedding <=> 'EMBEDDING_VECTOR'::vector
LIMIT 10;
```

If results have similarity < 0.3, they're likely not relevant — note this in the answer.

### Step 3: Optional Category Filter

If the question clearly targets one category (e.g., "What are competitors doing with AI?"), add a WHERE clause:

```sql
WHERE embedding IS NOT NULL AND category = 'competitors'
```

### Step 4: Read Matched Articles

For each of the top 10 results, read the full wiki article from disk at `knowledge-base/wiki/{slug}.md`. Reading from disk ensures you get the latest content (which may have been edited since last embedding).

### Step 5: Synthesize Answer

Using the matched articles as context, write a comprehensive answer to the question:

- Cite specific articles: "According to [[gohighlevel]], ..."
- Include relevant data points, quotes, and comparisons
- End with a `## Sources` section listing the articles used
- If the KB lacks sufficient information, say so explicitly and suggest what to ingest

### Step 6: Save Output

Write the answer to `knowledge-base/wiki/_outputs/{YYYY-MM-DD}-{question-slug}.md`:

```yaml
---
title: "Query: How does GoHighLevel's AI Employee compare?"
category: _output
query: "How does GoHighLevel's AI Employee compare to our chat widget?"
sources_used: ["wiki/competitors/gohighlevel.md", "wiki/technical/ai-employee-market.md"]
created: YYYY-MM-DD
---

[Answer content here]
```

### Step 7: File Back (Optional)

If the answer contains lasting insights not already in the wiki (e.g., a novel comparison, a synthesis that connects multiple articles), ask:

> "This answer contains insights that could enhance the wiki. Want me to file it back as a new article or merge into an existing one?"

If yes, create/update the appropriate wiki article and run embedding + Supabase upsert for it.

### Step 8: Report

Display the full answer in the terminal, then:

```
---
Answer saved to: knowledge-base/wiki/_outputs/2026-04-04-ghl-comparison.md
Sources consulted: 6 articles (similarity range: 0.72 — 0.91)
```
