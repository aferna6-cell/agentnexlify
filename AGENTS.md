# AgentNexLiFy Repository Guide

Use this file as a **thin adapter for Codex and general coding agents**.

## Agent-Facing Command Layer
Prefer these root commands before hunting through package files or ad-hoc scripts:

- `npm run check` - default quick verification alias.
- `npm run check:quick` - agent-system guardrail, product invariants, and widget sync check.
- `npm run check:instruction-budget` - fail if always-on Claude prompt injections or CLAUDE.md grow past budget.
- `npm run check:full` - quick checks plus frontend build and test suite.
- `npm run build` - production frontend build.
- `npm run test` - backend pytest plus frontend Vitest.
- `npm run smoke` - public smoke test.
- `npm run kb:health` - deterministic knowledge-base health report for stale articles, pending sources, coverage, attribution, orphan pages, and broken wikilinks.
- `npm run kb:lint` - validate wiki article template and index coverage.
- `npm run sync-widget` - copy canonical widget assets to deploy mirrors.
- `npm run sync-widget:check` - fail if widget mirrors drift.
- `npm run check:agent` - agent-system guardrail only.
- `npm run agent-config:scan` - pinned baseline-gated AgentShield scan for Claude/Codex agents, hooks, MCP config, and project instruction files.

Use narrower commands when a change is clearly isolated, but finish with the smallest command that covers the touched surface.

## Start Here
1. Read `PROMPTLIBRARY.md` first - it contains battle-tested prompts for every recurring task type.
2. Load `.codex/skills/agentnexlify-task-loader/SKILL.md` to select the smallest relevant skill and verification command.
3. Read `CLAUDE.md` for repo facts, invariants, and routing policy when the task needs broader context.
4. Read `.ai/manifest.json` when you need the machine-readable index of agents, skills, workflows, and routing policy.
5. Load the most relevant repo-local skill before editing:
   - `.claude/skills/prompt-library/SKILL.md` - use this workflow for ALL tasks
   - `.codex/skills/agentnexlify-task-loader/SKILL.md`
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
- `frontend/public/widget/` contains symlinks to `widget/` - always edit files in `widget/` directly.
- Use migrations in `migrations/` for schema changes.
- See `docs/dev-knowledge/canonical-schema.md` for authoritative database schema.
- Never commit raw secret values.
- Use dedicated MCP API keys for MCP access - not widget API keys.

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
- `backend/` - production FastAPI service
- `frontend/` - dashboard + public React/Vite app
- `widget/` - production embed widget
- `frontend/public/widget/` - widget mirror
- `docs/dev-knowledge/` - durable engineering memory
- `knowledge-base/` - structured knowledge inputs/outputs
- `.claude/` - Claude-oriented agents, skills, commands, hooks
- `.codex/` - Codex-native repo skills
- `skills/` - repo-level shared skills

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
- Default quick check: `npm run check`
- Full local check: `npm run check:full`
- Backend dev: `npm run dev:backend`
- Frontend dev: `npm run dev:frontend`
- Frontend build: `npm run build`
- Tests: `npm run test`
- Public smoke: `npm run smoke`
- KB health: `npm run kb:health`
- KB lint: `npm run kb:lint`
- Widget sync: `npm run sync-widget`
- Agent system check: `npm run agent-system:check`
- Instruction budget check: `npm run check:instruction-budget`
- Agent config security scan: `npm run agent-config:scan`
- Pinned Claude Code: `npm run claude:2.1.98 -- --version`

## Note
If this file and `CLAUDE.md` disagree, **follow `CLAUDE.md`** and then update this adapter.
