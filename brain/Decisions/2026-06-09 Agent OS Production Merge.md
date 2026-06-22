---
type: decision
decision_date: 2026-06-09
status: active
tags:
  - decision
source_status: source-backed
confidence: high
---

# Decision: Merge Agent OS into Production

## Decision
Vendor the [[Agent OS]] engine from the standalone `Agent-Nexlify-OS` repo into
`agentnexlify/agent-service/src/agent-os/` and make it the **only** agent path in production
(PRs #203–#208, #219). The canonical engine now lives in the `agentnexlify` repo.

## Rationale
Ship the conversational agent surface to real tenants on the production stack (real send,
plan caps, dashboard front door) rather than maintaining a separate demo-only product.

## Consequences
- Engine changes must be made in `agentnexlify`, not the spec repo (which becomes spec + demo).
- Graph-memory layer was built as part of this cutover (migration 133 + MemoryPanel).
- [[Agent Service]] became a production-critical component.

## Related
- [[Agent OS]] · [[Agent Service]] · [[Agent OS Graph Memory]]

## Provenance
- [[repo-agent-os-readme]] — merge banner + PR list
