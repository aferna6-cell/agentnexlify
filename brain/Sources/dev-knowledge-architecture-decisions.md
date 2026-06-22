---
type: source
source_id: dev-knowledge-architecture-decisions
origin: local-repo
path: /home/user/agentnexlify/docs/dev-knowledge/architecture-decisions.md
accessed: 2026-06-22
sensitivity: normal
tags: [source]
---

# Source: docs/dev-knowledge/architecture-decisions.md

## What this is
Running architecture decision log (ADR-style) for the backend/product.

## What it proves
- FastAPI + Supabase, no ORM (raw SQL numbered migrations).
- JWT for auth only; display data from live API (claims don't refresh on plan change).
- `chat_messages` is canonical message store (migration 006).
- SSE not WebSockets for widget streaming (2026-03-25).
- Vapi primary voice partner, Retell backup (thin adapter).
- Multi-tenant agency hierarchy: Platform > Agency > Business (white-label).
- No setup fees; prominent free tier (partner feedback).
- 4 Uvicorn workers in prod; per-process in-memory caches; 5-min widget config TTL.
- Compound "business operating system" thesis (modules share one data model → low churn).
