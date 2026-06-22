---
type: decision
decision_date: 2026-05-25
status: superseded-by-build
tags:
  - decision
  - agent-os
source_status: source-backed
confidence: high
---

# Decision: Agent OS Graph-Memory Layer

## Decision
Initially (2026-05-25) **defer** the Agent OS graph-memory layer beyond launch; ship semantic
memory only. Superseded **2026-06-09**: build it after the owner requested a "what do you know
about my business" view.

## Rationale
- Defer rationale: graph writes cost one LLM call per write.
- Reversal rationale: a concrete owner-requested feature justified the cost; implemented with
  one cheap Haiku call per owner turn (migration 133 + MemoryPanel) during the prod merge.

## Consequences
- Demonstrates the "defer until a real trigger, then build cheaply" pattern.

## Related
- [[Agent OS]] · [[2026-06-09 Agent OS Production Merge]] · [[Claude Model Routing]]

## Provenance
- [[planning-decision-graph-memory]]
