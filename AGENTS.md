# AgentNexLiFy Repository Guide

Use this file as a **thin adapter for Codex and general coding agents**.

## Start Here
1. Read `PROMPTLIBRARY.md` first — it contains battle-tested prompts for every recurring task type.
2. Read `CLAUDE.md` second — it is the canonical human-readable repo brain.
3. Read `.ai/manifest.json` third — it is the canonical machine-readable index of agents, skills, workflows, and routing policy.
4. Load the most relevant repo-local skill before editing:
   - `.claude/skills/prompt-library/SKILL.md` — use this workflow for ALL tasks
   - `.codex/skills/agentnexlify-surface-selector/SKILL.md`
   - `.codex/skills/agentnexlify-schema-guard/SKILL.md`
   - `.codex/skills/agentnexlify-runtime-constraints/SKILL.md`
   - `.codex/skills/agentnexlify-widget-integrity/SKILL.md`

## Canonical Sources
- **Repo brain:** `CLAUDE.md`
- **Machine-readable index:** `.ai/manifest.json`
- **Agent-system guardrail:** `scripts/check_agent_system.py`
- **Runtime AI audit:** `docs/AI_ARCHITECTURE_AUDIT.md`
- **Agent-system policy:** `docs/AGENT_SYSTEM_PLAN.md`
- **Architecture decisions:** `docs/dev-knowledge/architecture-decisions.md`
- **Schema history:** `docs/dev-knowledge/schema-log.md`
- **Bug memory:** `docs/dev-knowledge/bug-patterns.md`

## Critical Invariants
- Never use `from __future__ import annotations` in FastAPI router files.
- Use `client_id` for `leads` and `conversations` queries.
- Use `status` for lead status on the `leads` table.
- `frontend/public/widget/` contains symlinks to `widget/` — always edit files in `widget/` directly.
- Use migrations in `migrations/` for schema changes.
- See `docs/dev-knowledge/canonical-schema.md` for authoritative database schema.
- Never commit raw secret values.
- Use dedicated MCP API keys for MCP access — not widget API keys.

## Implementation Discipline
- Prefer the smallest concrete change that solves the observed problem.
- Do not add abstraction layers, adapter interfaces, factories, registries, or generic helpers for a single current call site.
- Do not add "just in case" fallbacks, legacy compatibility branches, broad coercion, or multi-shape input handling unless an existing production path or failing test proves the need.
- If a fallback is required, name the real failure mode in code or test context and add a regression test for that exact behavior.
- Fix the caller or data contract directly when possible instead of wrapping bad inputs with defensive normalization.
- Avoid catch-all `try`/`except` blocks that hide errors. If an exception is expected, catch the narrow type and assert/log the behavior being preserved.
- Tests should validate observable behavior and real contracts, not fallback plumbing or mock-only interactions.
- Before introducing a new helper, check whether the same logic is already expressed locally. If it is only used once, inline it unless it materially improves readability.

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
- **Sonnet/Haiku uncertainty:** when confidence is below 80%, evidence conflicts, or the task is high-stakes, consult Opus 4.7 as an advisor before execution instead of guessing

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
- Agent system check: `npm run agent-system:check`
- Pinned Claude Code: `npm run claude:2.1.98 -- --version`

## Note
If this file and `CLAUDE.md` disagree, **follow `CLAUDE.md`** and then update this adapter.
