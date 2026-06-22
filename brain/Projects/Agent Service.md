---
type: project
name: "Agent Service"
aliases:
  - "agent-service"
tags:
  - project
  - backend
source_status: source-backed
sensitivity: normal
status: production
last_verified: 2026-06-22
---

# Agent Service

## Summary
The Node/TypeScript service (`agentnexlify/agent-service/`) that now hosts the canonical
[[Agent OS]] engine, vendored in at the 2026-06-09 production merge
(`src/agent-os/`). It is the only agent path in production.

## Notes
- Engine changes go here, not in the `Agent-Nexlify-OS` spec repo.
- Has its own test suite + typecheck (verified green by a separate testing session 2026-06-22).

## Related
- [[Agent OS]] · [[2026-06-09 Agent OS Production Merge]] · [[AgentNexLiFy Platform]]

## Provenance
- [[repo-agent-os-readme]]
