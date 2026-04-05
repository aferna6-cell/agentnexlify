# Brainstorm: End-to-End Codebase Test
## Agent 1 Output — 2026-04-05

## Problem Statement
We need to verify the entire AgentNexLiFy codebase — 61 routers, 64 pages, 88 migrations, 18 services — is healthy across all verticals. This is the first test of the compound engineering pipeline itself, running it against the real codebase to catch latent issues.

## Constraints
- From CLAUDE.md: client_id (not tenant_id) for leads, status (not lead_stage), no `from __future__ import annotations` in routers, widget files must be identical
- 4 Uvicorn workers = in-memory state is per-process only
- Production runs on Railway (backend) + Vercel (frontend)
- Multi-tenant from day one — every query needs tenant filtering

## Edge Cases / Risk Areas
1. **Router registration gap**: 61 router files but only 60 `include_router` calls in main.py — one router may be orphaned
2. **Migration numbering**: CLAUDE.md mentions "some duplicate numbers at 005/007" — could cause ordering issues
3. **Widget desync**: Two copies of widget JS must be identical — any edit to one without the other is a production bug
4. **Schema drift**: 88 migrations over time — Pydantic models may reference columns that were renamed or dropped
5. **Dead code**: With 61 routers and 64 pages, likely some unused endpoints or pages
6. **Security surface**: 61 routers = 61 attack surfaces. Each needs auth + tenant filtering
7. **Frontend build**: With 141 JS files, missing imports or stale references could break the build

## Dependencies
- Backend depends on: Supabase (DB), Anthropic (AI), Resend (email), Twilio (SMS), Stripe (payments)
- Frontend depends on: Backend API, Vite build system
- Widget depends on: Backend chat API, tenant config API

## Prior Art
- Existing qa-tester agent checks a subset of these
- Existing schema-guardian checks schema integrity
- Existing security-audit skill scans for vulnerabilities
- The vertical-checker agent we just created combines all of these

## Approaches
1. **Sequential full scan** — One agent checks everything top to bottom. Thorough but slow.
2. **Parallel vertical scan** — 6 agents, one per vertical, all running simultaneously. Fast, focused, but needs coordination.
3. **Hybrid** — Core checks inline (fast), deep dives delegated to parallel agents.

## Recommendation
**Approach 3: Hybrid.** Run the fast deterministic checks inline (grep scans, diff, build check) and delegate the deep analysis (security audit, performance profiling, schema consistency) to parallel agents. This gives us speed where checks are mechanical and depth where they need judgment.

## Open Questions
1. Which router is missing from main.py registration?
2. What's the state of the duplicate migration numbers (005/007)?
3. Are there any routers that import `from __future__ import annotations`?
4. How many endpoints lack tenant filtering?
