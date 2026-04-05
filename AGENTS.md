# AgentNexLiFy Repository Guide

Use this file as a **thin adapter for Codex and general coding agents**.

## Start Here
1. Read `CLAUDE.md` first — it is the canonical human-readable repo brain.
2. Read `.ai/manifest.json` second — it is the canonical machine-readable index of agents, skills, workflows, and routing policy.
3. Load the most relevant repo-local skill before editing:
   - `.codex/skills/agentnexlify-surface-selector/SKILL.md`
   - `.codex/skills/agentnexlify-schema-guard/SKILL.md`
   - `.codex/skills/agentnexlify-runtime-constraints/SKILL.md`
   - `.codex/skills/agentnexlify-widget-integrity/SKILL.md`

## Canonical Sources
- **Repo brain:** `CLAUDE.md`
- **Machine-readable index:** `.ai/manifest.json`
- **Runtime AI audit:** `docs/AI_ARCHITECTURE_AUDIT.md`
- **Agent-system policy:** `docs/AGENT_SYSTEM_PLAN.md`
- **Architecture decisions:** `docs/dev-knowledge/architecture-decisions.md`
- **Schema history:** `docs/dev-knowledge/schema-log.md`
- **Bug memory:** `docs/dev-knowledge/bug-patterns.md`

## Critical Invariants
- Never use `from __future__ import annotations` in FastAPI router files.
- Use `client_id` for `leads` and `conversations` queries.
- Use `status` for lead status on the `leads` table.
- Keep `widget/agentnexlify-widget.js` and `frontend/public/widget/agentnexlify-widget.js` identical.
- Use migrations in `migrations/` for schema changes.
- Never commit raw secret values.
- Use dedicated MCP API keys for MCP access — not widget API keys.

## Surface Map
- `backend/` — production FastAPI service
- `frontend/` — dashboard + public React/Vite app
- `widget/` — production embed widget
- `frontend/public/widget/` — widget mirror
- `docs/dev-knowledge/` — durable engineering memory
- `knowledge-base/` — structured knowledge inputs/outputs
- `.claude/` — Claude-oriented agents, skills, commands, hooks
- `.codex/` — Codex-native repo skills
- `skills/` — repo-level shared skills

## Model Routing Policy
- **Codex:** primary execution engine for implementation, debugging, refactors, tests
- **Anthropic:** canonical repo brain and production customer-facing runtime AI authority
- **MiniMax:** cheap triage, summarization, and lightweight helper/subagent work

## Default Delegation Pattern
For non-trivial coding work:
1. `schema-guardian` when schema-sensitive
2. `backend-dev` and/or `frontend-dev`
3. `widget-specialist` when the chat widget or embed contract is involved
4. `qa-tester` before done
5. `security-reviewer` for auth/payment/MCP/AI trust-boundary work

## Commands
- Backend dev: `uvicorn backend.main:app --reload --port 8000`
- Frontend dev: `cd frontend && npm run dev`
- Frontend build: `cd frontend && npm run build`

## Note
If this file and `CLAUDE.md` disagree, **follow `CLAUDE.md`** and then update this adapter.
