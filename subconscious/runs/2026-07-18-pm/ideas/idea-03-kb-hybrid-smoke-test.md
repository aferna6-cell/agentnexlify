# Idea 03 — KB Hybrid + Rerank Production Smoke Test

**Category:** Operational / Code Health
**Effort:** S (diagnostic script or Step 9G in nightly SKILL.md)
**Confidence:** MEDIUM
**ROI:** 1.7

## The Idea

PR #476 seeded `widget_kb_hybrid_enabled=1` and `widget_kb_rerank_enabled=1` in prod today
without a validation step. Both features are fail-open — but fail-open means silent failure
is indistinguishable from working. A daily diagnostic would confirm the features are functional.

## Evidence

- `kb_hybrid_retrieval.py`: FTS pass via `match_kb_articles_fts` RPC (migrations 155/163).
  If RPC fails: returns `semantic_rows` unchanged. Silent fallback.
- `kb_reranker.py`: Haiku reranker, 6s timeout. If LLM error: returns original list. Silent fallback.
- `widget_kb_hybrid_enabled=1` set today (PR #476). No prod test run yet.
- Historical precedent: KB autopopulate was dark 72 days with zero automated signal (Step 9F is
  the fix for that). Same class of problem here — silent failure with no alerting.

## Implementation Sketch

Add Step 9G to nightly SKILL.md:
```bash
# Check if hybrid retrieval is returning FTS results (not just falling back)
# Look for recent widget chat logs where hybrid path fired
# Log: "Step 9G: kb_hybrid firing: YES/NO/UNKNOWN"
```

Or: standalone `scripts/daily/validate-kb-features.sh` that makes a test widget call and
checks if FTS results appear in the retrieval log.

## Why It's WEAKENED

- Both features are fail-open — user experience unchanged whether working or not.
- No immediate customer pain signal.
- Implementation requires either a new script (S-effort, GH #399 blocks) or a SKILL.md step
  (valid channel but would be Step 9G — premature when Step 9F hasn't fired once yet).
- Better approach: let Step 9F run first, then add Step 9G as a natural extension.

## Verdict

WEAKENED → parking lot. Run 100+ candidate once Step 9F is confirmed firing.
