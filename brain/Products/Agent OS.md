---
type: product
name: "Agent OS"
aliases:
  - "Agent-Nexlify-OS"
  - "AgentNexLiFy OS"
tags:
  - product
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Agent OS

## Summary
The conversational agent layer for [[AgentNexLiFy Platform]]. A business owner talks to one
**orchestrator** in plain English; it routes to a best-fit worker/department-head agent, which
runs, streams an honest reasoning trace, and produces a **draft for approval** (see
[[Drafts-Only Approval Loop]]).

## Status
- **Merged into production 2026-06-09** (agentnexlify PRs #203–#208, #219). Canonical engine
  vendored into `agentnexlify/agent-service/src/agent-os/`; the `Agent-Nexlify-OS` repo is now
  spec + offline demo. Governed by [[2026-06-09 Agent OS Production Merge]].
- Graph-memory layer built 2026-06-09 (migration 133 + MemoryPanel) — see [[Agent OS Graph Memory]].

## v2 model
- Owner talks to 8 department-head agents (Sales, Marketing, Customer Service, Operations,
  Invoicing & Collections, Accounting & Finance, Customer Data & Administration, People
  Management); each bundles former specialist workers as internal skills. Consolidation from
  18 specialists → 8 heads is a separate future sprint. Source: [[repo-agent-os-readme]]

## Stack (standalone repo)
- Next.js 15 + TypeScript + Prisma + `@anthropic-ai/sdk`; SQLite offline / Postgres prod.
- Live demo: https://agent-nexlify-os.vercel.app (demo bypass "Maya"; seeded "Sunset Auto Care").

## Related
- [[AgentNexLiFy Platform]] · [[Agent Service]] · [[Claude Managed Agents]] · [[Advisor-Executor Pattern]]

## Provenance
- [[repo-agent-os-readme]] · [[planning-decision-graph-memory]]
