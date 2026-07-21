# Memory Hygiene — Confidence, Freshness, Eviction

Governs the file-based cross-session memory (`~/.claude/projects/<project>/memory/*.md`).
Prevents uncontrolled memory growth (UMG) and false-memory propagation (FMP):
memory that grows forever, carries no confidence, and never expires becomes a
source of confident-but-wrong recommendations. Issue #68.

## Frontmatter schema

Every memory `*.md` file carries these managed fields in its YAML frontmatter
(the `MEMORY.md` index file is exempt):

```yaml
---
confidence: 0.8            # float 0.0-1.0 — how much to trust this memory
last_verified: 2026-07-21T00:00:00+00:00   # ISO-8601 — last time confirmed true
access_count: 0           # int — times this memory was read/used
---
```

Backfill existing files (idempotent, `--dry-run` supported):

```bash
python3 scripts/memory/backfill_frontmatter.py --dry-run   # preview
python3 scripts/memory/backfill_frontmatter.py             # apply
```

The script resolves the memory dir from `--dir`, then `$CLAUDE_MEMORY_DIR`, then
the per-project convention — it never hardcodes a user-specific path.

## Setting confidence on write

- **0.9-1.0** — verified against source this session (ran the code, read the
  file, confirmed with the user).
- **0.7-0.8** — inferred from strong evidence but not directly confirmed
  (default for new memories is `0.8`).
- **0.4-0.6** — a guess or a single unconfirmed signal.
- **< 0.4** — speculative; prefer not to persist at all.

Set `last_verified` to now whenever you re-confirm a memory is still true. Bump
`access_count` when a memory actually informs an answer.

## Decrement on contradiction

When new evidence contradicts a stored memory:

1. Trust the fresh evidence over the stored memory (code/tests/user > memory).
2. Lower that memory's `confidence` (roughly halve it), or rewrite the memory to
   match reality and set `confidence` high with a fresh `last_verified`.
3. Never silently keep both the old and new claim — reconcile to one.

## Before recommending from memory

Weight a memory by `confidence` and `last_verified`. Treat a memory as stale
when `last_verified` is older than 90 days — re-verify before acting on it, and
say so if you cannot.

## Eviction threshold

A memory is eligible for deletion when ALL hold:

```
confidence < 0.2  AND  access_count < 3  AND  age(last_verified) > 90 days
```

Low trust, rarely used, and old — it is noise. Deletion is a human-approved or
explicitly-invoked step (this rule defines the threshold; it does not auto-delete).

## Constraints

- Never modify the `MEMORY.md` index via the backfill — only individual files.
- Preserve existing frontmatter fields, their order, and the article body.
- This rule is about `/memory/` only. Knowledge-base article provenance is a
  separate concern (issue #70, `.claude/rules/kb-first.md`,
  `backend/services/kb_provenance.py`).

## Cross-refs
- `scripts/memory/backfill_frontmatter.py` — schema backfill tool
- `.claude/rules/memory-tiered-retrieval.md` — 3-layer retrieval (reads memory)
- `.claude/rules/one-task-one-chat.md` — session/memory hygiene between tasks
- Source: agent-memory analysis 2026-04-20 (UMG / FMP risk)
