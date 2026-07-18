# Idea 05 — conversation_enrichment_job.py Nightly Schedule GH Issue

**Category:** Operational / AI Performance
**Effort:** XS (file GH issue with complete sketch) — S (implement schedule)
**Confidence:** MEDIUM
**ROI:** 1.6

## The Idea

PR #471 (2026-07-17) shipped `batch_runtime.py` + `conversation_enrichment_job.py`.
The batch variant for nightly conversation enrichment exists but has no schedule.
File a GH issue with complete implementation sketch + ai-ready label, queue for GH #399 resolution.

## Evidence

- `batch_runtime.py`: wraps Anthropic Message Batches (50% cost reduction for offline jobs).
  `submit_batch`, `poll_batch`, `get_batch_results` — never raise, offline-safe.
- `conversation_enrichment_job.py`: enriches past conversations with metadata.
  Batch variant added in PR #471. No nightly trigger.
- Pending conversations: unknown count (Supabase MCP unavailable in headless sessions).
  Likely non-trivial — conversations have been accumulating since platform launch.
- GH #399 blocks issue-to-pr-loop (30 ai-ready issues queued). Any new GH issue joins blocked queue.

## Implementation Sketch

```python
# In scripts/daily/conversation-enrichment-nightly.sh
# OR as new GitHub Action: .github/workflows/conversation-enrichment.yml
# Schedule: 0 3 * * * (3am UTC, after nightly-commit-review)
# WHERE clause: conversations where enriched_at IS NULL, created >7 days ago
# Batch submit → poll → store results
# Guard: skip if batch API unavailable, fail-open
```

## Why It's WEAKENED

- GH #399 blocks issue-to-pr-loop. Filing a GH issue adds to a queue of 30+ blocked items.
- Pending conversation count unknown (headless, no Supabase MCP).
- Cannot determine urgency without knowing how many conversations need enrichment.
- Better path: investigate conversation queue size first (run 99 mandate check 6 — depends on
  GH #399 resolution).

## Verdict

WEAKENED → parking lot. Re-evaluate when GH #399 resolved + Supabase MCP available.
Mandate: run 100 should check conversation count if GH #399 resolved by then.
