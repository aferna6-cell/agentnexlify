---
type: topic
name: "Advisor-Executor Pattern"
tags:
  - topic
  - agent-design
  - cost
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Advisor-Executor Pattern

## Definition
A cost-control agent pattern: **Opus 4.7 advises** (read-only brief) → **Sonnet executes** →
**Haiku cleans**. Delivers near-Opus quality at ~1.3x pure-Sonnet cost instead of ~5x pure-Opus.

## Where it's used
- Dev-time: `opus-advisor` + `sonnet-executor` subagents.
- Product-runtime: `backend/services/advisor_executor.py` (mirrors the pattern for tenant-facing
  Managed Agents).

## Related
- [[Claude Model Routing]] · [[Claude Managed Agents]] · [[Agent OS]] · [[User Engineering Rules]]

## Provenance
- [[repo-agentnexlify-claude-md]] (model-routing rule) · [[docs-managed-agents]]
