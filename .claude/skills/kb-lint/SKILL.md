---
name: kb-lint
description: Validate every wiki article against the Karpathy template — frontmatter fields, required sections, ≥1 wikilink, banned filler phrases, INDEX.md coverage. Use when user says 'kb-lint', 'lint wiki', 'check wiki', 'validate wiki', 'lint knowledge base', or asks about wiki quality violations.
version: 1.0.0
origin: claude
user_invocable: true
triggers:
- kb-lint
- lint wiki
- check wiki
- validate wiki
- lint knowledge base
effort: low
---

# KB Lint — Wiki Validator

Fast, deterministic validator for the LLM wiki. Runs in <1s across all articles.

## Usage

```bash
python3 scripts/kb/kb-lint.py                # lint all articles
python3 scripts/kb/kb-lint.py --fix-index    # also verify INDEX.md coverage
python3 scripts/kb/kb-lint.py --json         # machine-readable output
```

Exit code `1` on any violation — safe to wire into CI / pre-commit hook.

## When to Use
- Before committing new wiki articles
- After `/kb-compile` to catch orphaned articles (missing from INDEX)
- Scheduled CI check — fail the build on template drift
- When wiki feels "off" and you want a quick diagnosis

## When NOT to Use
- Semantic correctness (use `/kb-health` for staleness, contradictions, gaps)
- Embedding verification (use `/kb-query` to confirm semantic search works)
- Adding new sources (use `/kb-ingest`)

## Rules Enforced

Every wiki article MUST have:

1. **YAML frontmatter** with required fields: `title`, `category`, `tags`, `sources`, `created`, `updated`, `summary`
2. **Summary** — one sentence, ≥20 chars
3. **Three required sections**:
   - `## Key Concepts`
   - `## Related Articles`
   - `## Relevance to AgentNexLiFy`
4. **≥1 `[[wikilink]]`** — every article cross-references at least one other
5. **No banned filler phrases** — "It's worth noting that", "Interestingly,", "It should be mentioned that", "As we can see,", "In conclusion,"
6. **Word count** — 200–3000 words

With `--fix-index`, also verifies every wiki file has an entry in `knowledge-base/INDEX.md`.

## Output Format

```
knowledge-base/wiki/competitors/foo.md
  - frontmatter missing field: summary
  - missing section: ## Key Concepts
  - no [[wikilinks]] — every article must link to ≥1 other

3 violations across 1 files
```

Or with `--json`:

```json
{
  "articles_checked": 11,
  "violations_by_file": {...},
  "index_issues": [...],
  "total_violations": 9
}
```

## Integration Points

- **Pre-commit**: add to `.git/hooks/pre-commit` for articles in staged changes
- **CI**: `.github/workflows/kb-lint.yml` — fail PRs that violate template
- **Cron**: `scripts/daily/kb-autopopulate.sh` should call this post-compile to catch orphans

## Extending

New rules live in `scripts/kb/kb-lint.py`:
- Frontmatter field → add to `REQUIRED_FRONTMATTER`
- Required section → add to `REQUIRED_SECTIONS`
- Banned phrase → add to `BANNED_PHRASES`
- New check → new function + call in `lint_article()`

Keep rules fast and deterministic. No LLM calls — this is the syntactic gate, `/kb-health` is the semantic gate.

## Example Run

```
$ python3 scripts/kb/kb-lint.py --fix-index
knowledge-base/wiki/competitors/competitive-landscape-march-2026.md
  - frontmatter missing field: summary
  - missing section: ## Key Concepts
  - missing section: ## Related Articles

9 violations across 3 files
```

Pre-existing articles (pre-template) surface here. Fix or grandfather via explicit allowlist in script.
