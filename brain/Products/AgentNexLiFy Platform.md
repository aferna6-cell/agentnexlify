---
type: product
name: "AgentNexLiFy Platform"
aliases:
  - "the platform"
  - "the dashboard product"
tags:
  - product
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# AgentNexLiFy Platform

## Summary
The core product of [[AgentNexLiFy]]: a multi-tenant SaaS pairing an embeddable
[[Chat Widget]] with a React/Vite [[Dashboard]], backed by a FastAPI service on Supabase.
It captures leads, books appointments, answers visitor questions, and runs follow-up
workflows for small service businesses.

## Surfaces
- [[Chat Widget]] — embeddable `<script>` with `data-api-key="anx_..."`. Source: [[docs-deployment-surfaces]]
- [[Dashboard]] — `app.agentnexlify.com`, ~35 API domain modules (CRM, conversations, pipeline, billing). Source: [[docs-deployment-surfaces]]
- [[Agent OS]] — conversational agent layer (merged into prod 2026-06-09).
- Hosted business pages — `agentnexlify.com/biz/{slug}` for owners without a website. Source: [[dev-knowledge-architecture-decisions]]

## Plans
- `chatbot` $19.99/mo (widget/chat only) · `agent_os` $99.99/mo (full platform) · `free` internal.
  Governed by [[2026-06-15 Plan Repricing]].

## Tech
- FastAPI (Railway) + React 18/Vite 6 (Vercel) + Supabase Postgres/RLS/pgvector + Claude.
  4 Uvicorn workers; per-process caches. Source: [[dev-knowledge-architecture-decisions]]

## Live data (Supabase smoke pass 2026-06-22)
- Active DB `pxserpybmajixqrmzaly` (org [[VoltOps]]): ~130 tables, RLS on all. 12 tenants,
  1051 conversations, 2706 chat_messages, 27 leads, 92 FAQ entries. `os_*` tables populated →
  [[Agent OS]] live in prod. Source: [[connector-supabase-schema]]

## Key invariants
- [[client_id vs tenant_id]] · [[Widget Byte-Identical Sync]] · no `from __future__ import annotations`.

## Related
- [[AgentNexLiFy]] · [[Agent OS]] · [[Claude Managed Agents]] · [[Multi-Tenant Architecture]]

## Provenance
- [[repo-agentnexlify-readme]] · [[repo-agentnexlify-claude-md]] · [[docs-deployment-surfaces]] · [[dev-knowledge-architecture-decisions]] · [[connector-supabase-schema]]
