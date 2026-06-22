---
type: context-pack
scope: "Implement and ship a feature in the AgentNexLiFy codebase"
tags:
  - context-pack
last_updated: 2026-06-22
---

# Context Pack: Ship a Feature in AgentNexLiFy

## Use This When
An agent needs to add or change a feature in the `agentnexlify` codebase end-to-end.

## Essential Context
- Product: [[AgentNexLiFy Platform]] (FastAPI + React/Vite + Supabase + Claude).
- Architecture: [[Multi-Tenant Architecture]]; schema rule [[client_id vs tenant_id]].
- Agent layer: [[Agent OS]] lives in [[Agent Service]] (`agent-service/src/agent-os/`).
- AI usage: route models per [[Claude Model Routing]] + [[Advisor-Executor Pattern]].

## Current State
- Full test suite is green as of 2026-06-22 (root 1084 / backend 1088 / frontend 140 pass).

## Relevant Procedures
- [[Daily Skills Gate]] (plan→grill→issues→TDD→build)
- [[Database Migration Workflow]] (schema changes)
- [[Widget Byte-Identical Sync]] (widget edits)
- [[Local Release Gate]] then [[Production Deploy]]

## Hard Invariants
- `client_id` not `tenant_id` on leads/conversations; `status` not `lead_stage`;
  `areas_of_interest` not `service_interest`.
- No `from __future__ import annotations` in FastAPI files.
- Widget must stay byte-identical across mirrors.

## Open Loops
- See [[Open Loops]].

## Sources
- [[repo-agentnexlify-claude-md]] · [[dev-knowledge-architecture-decisions]] · [[dev-knowledge-canonical-schema]]

## Agent Instructions
- Do not assume facts not present in linked notes.
- Follow [[User Engineering Rules]]: plan first, ask <80% confidence, tests first.
- Check [[SOURCE-MANIFEST]] for source freshness.
- Never perform external writes (deploys, DB writes, sends) without explicit approval.
