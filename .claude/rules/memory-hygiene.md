# Memory Hygiene — Confidence + Staleness + Eviction

## Problem
Memory files grow without bound. Without a confidence score or staleness signal, false memories propagate silently (FMP) and old entries never get evicted (UMG — uncontrolled memory growth). CLAUDE.md already says "verify before recommending" — this rule makes that verifiable.

## Schema

Every memory file (except MEMORY.md) must have these frontmatter fields:

```yaml
---
name: <short name>
description: <one-line description>
type: user | feedback | project | reference
confidence: 0.8          # float 0.0–1.0
last_verified: 2026-04-20T00:00:00Z  # ISO8601 UTC
access_count: 0          # int, incremented each time the memory informs a decision
---
```

Existing fields (`originSessionId`, etc.) may also be present — preserve field order.

## Setting confidence on write

| Situation | confidence |
|-----------|-----------|
| Directly observed / just verified against live state | 1.0 |
| Inferred from context, likely correct | 0.8 (default) |
| Based on user statement, not verified in code | 0.7 |
| Reconstructed from old conversation / partial signal | 0.5 |
| Speculative or single-data-point | 0.3 |

## Decrementing confidence on contradiction

When new evidence contradicts a memory:
1. Read the file.
2. Lower `confidence` by 0.2 (floor at 0.0).
3. Update the body to record the contradiction inline.
4. Set `last_verified` to now.
5. If confidence drops below 0.2, evaluate the eviction rule.

## Incrementing access_count

When a memory directly informs a recommendation or decision in a session, increment `access_count` by 1. A memory that is never accessed accumulates evidence it should be evicted.

## Eviction rule

Delete (or archive) a memory file when ALL three conditions hold:

| Condition | Threshold |
|-----------|-----------|
| `confidence` | < 0.2 |
| `access_count` | < 3 |
| Age (today − `last_verified`) | > 90 days |

Eviction is a manual step — review before deleting. Add a note in MEMORY.md if the entry was load-bearing before eviction.

## Backfill

New fields can be added to existing memory files with:

```bash
python scripts/memory/backfill_frontmatter.py --dry-run   # preview changes
python scripts/memory/backfill_frontmatter.py              # apply
```

The script is idempotent — safe to re-run.

## Anti-patterns

- Never set `confidence: 1.0` without verifying against current code/state.
- Never skip updating `last_verified` when you correct a memory.
- Never let `confidence` drift below eviction threshold without deciding to evict.
- Never write `access_count` manually to inflate it — it is a passive counter.

## Cross-refs
- `~/.claude/CLAUDE.md` — memory schema section
- `scripts/memory/backfill_frontmatter.py` — backfill tool
- CLAUDE.md (project) — "Before recommending from memory" rule
