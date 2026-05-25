# Decision — Agent OS graph-memory layer (defer past launch)

**Date:** 2026-05-25
**Status:** decided — defer
**Owner:** Aidan
**Source:** `specs/agent-os-overhaul_spec.md` Open Questions §4; `plans/agent-os-p0_plan.md` decision #2; `plans/agent-os-next-steps_plan.md` §2

## Context

P0 shipped semantic memory only — `os_memory_entries` table, Voyage `voyage-3-lite`
512d embeddings, cosine ANN via `match_os_memory` SQL function
(`backend/services/os_memory.py:65-88`). The Karpathy graph layer
(`os_memory_nodes` + `os_memory_edges`) was cut from P0 with re-decision
scheduled for end of P1.

P1-P4 worker agents are now shipped on the branch (5 workers auto-discovered in
`backend/services/os_workers/`). MVP loop end-to-end test passes
(`tests/test_os_mvp_e2e.py`). Time to decide.

## The two layers (from the overhaul spec §Memory architecture)

1. **Semantic layer** — memory slices embedded with Voyage AI + stored in
   pgvector. Retrieval = top-k cosine similarity against the current prompt.
   Cost: one embedding call per write (~$0 at Voyage rates).
2. **Graph layer** — entity pages with typed relationships
   (Karpathy LLM-wiki pattern, `knowledge-base/wiki/ai-llm/llm-wiki-karpathy-pattern.md`).
   Each new source updates relevant entity pages. Cost: one LLM call per memory
   write (entity-page update + edge inference).

## Decision

**Defer the graph layer indefinitely.** Ship launch on semantic-only. Revisit
only if/when production usage produces concrete recall failures the semantic
layer cannot solve.

## Reasoning

1. **No production data yet.** Goal is 5 paying tenants in 90 days. We have
   zero tenants on Agent OS today. Building a graph layer now optimizes for a
   recall problem we have not observed.
2. **Cost asymmetry is real.** Graph layer = one LLM call per memory write.
   At scale (100s of writes per tenant per day), that's a per-tenant Opus/Sonnet
   recurring spend that compresses the ~5:1 margin in the cost model
   (`specs/agent-os-overhaul_spec.md` §Cost model, illustrative ~$500/mo plan
   with ~$100 of API usage).
3. **Semantic layer is good enough for the launch workflows.** P1-P4 worker
   agents (customer_question, booking, lead_nurture, campaign) read memory
   via `search_memory()` — top-k retrieval against the user's current prompt.
   For "what's our pricing?", "when did this lead last engage?", "what did the
   owner decide about Sundays?" — cosine ANN on the slice corpus is sufficient.
4. **Build-only-what's-needed wins twice.** Cut now = less code to ship + less
   code to refactor when real recall data arrives. The graph layer can be
   added later without breaking the semantic surface (additive migration,
   `os_memory_entries` rows are not touched).
5. **The spec already named graph as the cut candidate** (§Memory architecture,
   line 180-182): "If a simpler design proves sufficient during the Phase 1
   build, the graph layer is the cut candidate — flag to owner before cutting."
   This decision IS that flag.

## Revisit triggers (when to build graph layer as P5)

Build the graph layer only if any of these fire in production:

- **Cross-thread entity recall failure** — owner asks "what did Sarah say about
  the Smith job?" and the orchestrator returns nothing because the relevant
  slice was embedded under a thread about Smith, not Sarah. (Symptom: semantic
  search fails on entity-pivoted queries even when the data exists.)
- **Memory bloat** — `os_memory_entries` past ~10k rows per tenant with
  retrieval quality degrading. (Graph entity pages compress N slices about one
  entity into one summary.)
- **Recurring-customer recognition** — booking/lead-nurture workers
  consistently fail to recognize returning customers because slices reference
  them by inconsistent names. (Graph entity dedup solves this.)
- **Owner-requested feature** — "show me everything you remember about X" as a
  navigable view. The semantic layer can't surface a structured entity profile;
  the graph layer can.

Quantitative gate: when >=20% of agent runs surface "I don't have that
information" on queries where the data demonstrably exists in
`os_memory_entries`, scope graph as P5.

## Cost of revisiting later

Additive migration (next free number at that time):

- `os_memory_nodes` table (`client_id`, `entity_type`, `name`, `summary`,
  `attributes` JSON, embedding for entity-name search).
- `os_memory_edges` table (`client_id`, `from_node`, `to_node`, `relation`).
- Background job to backfill nodes from existing `os_memory_entries`
  (one-time Opus pass per tenant).
- Update `write_memory()` in `backend/services/os_memory.py` to fan out to
  entity-page update (one extra LLM call per write).
- Update `search_memory()` to optionally walk the graph for entity-pivoted
  queries.

Estimated effort when triggered: ~1 week of build + 1 week of recall-quality
A/B before deciding to keep it on.

## What this decision does NOT change

- Semantic-only memory ships at launch — already done.
- Owner-only edit/delete enforced at router layer — already done.
- Explicit "remember this" via `is_pinned` — already done.
- Spec text in `specs/agent-os-overhaul_spec.md` §Memory architecture stays
  accurate (the layer was always flagged as "cut candidate if simpler design
  sufficient"). No spec revision needed.

## Cross-refs

- `specs/agent-os-overhaul_spec.md` §Memory architecture, §Open Questions
- `plans/agent-os-p0_plan.md` decision #2
- `plans/agent-os-next-steps_plan.md` §2
- `backend/services/os_memory.py` — semantic layer implementation
- `knowledge-base/wiki/ai-llm/llm-wiki-karpathy-pattern.md` — the pattern we're
  deferring
- `migrations/121_os_memory_entries.sql` — semantic layer table
