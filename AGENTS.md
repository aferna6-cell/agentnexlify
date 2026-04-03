# AgentNexLiFy Repository Guide

## Purpose
- Use this file to orient quickly before editing code in this repository.
- Read `CLAUDE.md` first for complete project rules, then load skills that match the task.
- For a machine-readable index of all AI resources (skills, agents, workflows), see `.ai/manifest.json`.

## AI Agent Configuration Files

This repo provides instructions for multiple AI coding tools:

| File | Tool |
|------|------|
| `CLAUDE.md` | Claude Code (primary, most complete) |
| `AGENTS.md` | OpenAI Codex / general agents (this file) |
| `GEMINI.md` | Google Gemini CLI |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.cursorrules` | Cursor AI |
| `.windsurfrules` | Windsurf / Codeium |
| `.clinerules` | Cline / Roo Code |
| `.aider.conf.yml` | Aider CLI |
| `.ai/manifest.json` | Universal machine-readable manifest |

## Repo Shape
- `backend/`: the production FastAPI service. One app in [`backend/main.py`](/home/aidan/agentnexlify/backend/main.py) serves the API, mounts `/widget`, and starts the automation loop.
- `frontend/`: the primary Vite/React app. It contains public marketing routes, public business pages, and the authenticated dashboard.
- `widget/`: the production widget bundle served by the backend. This is the live embed surface.
- `demo-platform/`: a separate demo/sales app with its own optional FastAPI server. Treat it as isolated from production unless the task explicitly targets demos.
- `landing-page-v2/` and `public/`: older parallel frontend/widget lines. Do not touch them unless the request is explicitly about those surfaces or a migration away from them.
- `_archive/`: retired code and old scripts kept for reference only.
- `migrations/`: the clearest record of the live schema, but numbering is not perfectly tidy.
- `prospects/`: prospecting/import utilities and data, not product runtime code.

## Main Subsystems
- Widget chat runtime: [`backend/routers/widget.py`](/home/aidan/agentnexlify/backend/routers/widget.py) plus [`widget/agentnexlify-widget.js`](/home/aidan/agentnexlify/widget/agentnexlify-widget.js).
- Tenant auth and dashboard API: [`backend/routers/auth.py`](/home/aidan/agentnexlify/backend/routers/auth.py).
- CRM and lead operations: [`backend/routers/clients.py`](/home/aidan/agentnexlify/backend/routers/clients.py), [`backend/routers/leads.py`](/home/aidan/agentnexlify/backend/routers/leads.py), [`backend/routers/analytics.py`](/home/aidan/agentnexlify/backend/routers/analytics.py).
- Scheduling and Google Calendar: [`backend/routers/appointments.py`](/home/aidan/agentnexlify/backend/routers/appointments.py), [`backend/routers/integrations.py`](/home/aidan/agentnexlify/backend/routers/integrations.py), [`backend/services/booking.py`](/home/aidan/agentnexlify/backend/services/booking.py).
- Automations, SMS, email: [`backend/routers/sequences.py`](/home/aidan/agentnexlify/backend/routers/sequences.py), [`backend/routers/automations.py`](/home/aidan/agentnexlify/backend/routers/automations.py), [`backend/services/automation_engine.py`](/home/aidan/agentnexlify/backend/services/automation_engine.py).
- Billing and outbound webhooks: [`backend/routers/billing.py`](/home/aidan/agentnexlify/backend/routers/billing.py), [`backend/routers/stripe_webhooks.py`](/home/aidan/agentnexlify/backend/routers/stripe_webhooks.py), [`backend/routers/webhooks.py`](/home/aidan/agentnexlify/backend/routers/webhooks.py).
- Hosted business pages: [`backend/routers/business_page.py`](/home/aidan/agentnexlify/backend/routers/business_page.py) and [`frontend/src/pages/BusinessPage.jsx`](/home/aidan/agentnexlify/frontend/src/pages/BusinessPage.jsx).

## High-Risk Invariants
- Do not add `from __future__ import annotations` to FastAPI router files. This repo already documents that it breaks request model handling.
- Auth, JWTs, and most tables use `tenant_id`; the `leads` table still uses `client_id`. Check the existing query pattern before changing lead-related code.
- Lead stage is stored in `status`, not `lead_stage`.
- The current production widget contract uses `data-api-key` and optional `data-brand-color` / `data-api-base`.
- [`widget/agentnexlify-widget.js`](/home/aidan/agentnexlify/widget/agentnexlify-widget.js) and [`frontend/public/widget/agentnexlify-widget.js`](/home/aidan/agentnexlify/frontend/public/widget/agentnexlify-widget.js) must stay identical.
- Active chat history is stored in `chat_messages`. [`backend/services/conversation.py`](/home/aidan/agentnexlify/backend/services/conversation.py) reflects an older conversation-storage approach and should be treated as stale unless the task is explicitly reviving it.
- Current plan names are `free`, `growth`, `professional`, `enterprise`. Do not introduce older plan labels.
- Production backend runs with 4 Uvicorn workers. In-memory counters, caches, and loops are per-process only; do not treat them as globally authoritative.

## Working Rules
- Prefer source files over committed build output. Ignore `dist/` and `node_modules/` unless the task is explicitly about shipped artifacts.
- Treat audit documents (`FULL_AUDIT.md`, `PRE_LAUNCH_AUDIT.md`, `CLEANUP_REPORT.md`, `AUDIT_RESULTS.md`) as hints. Re-verify every claim in the live code before acting on it.
- When a task touches widget behavior, check both the backend widget API and the frontend/business-page embed path.
- When a task touches schema, migrations, or lead handling, load the schema guard skill before editing.
- When a task is demo-only, keep production code untouched unless the user asks for shared fixes.
- Avoid routing new work into `landing-page-v2/`, `public/`, or `_archive/` unless the task is explicitly about legacy cleanup or migration.

## Repo-Local Skills
- `agentnexlify-surface-selector`: choose the right surface or subsystem before editing.
- `agentnexlify-schema-guard`: protect live schema conventions and backend data/query invariants.
- `agentnexlify-widget-integrity`: keep the current production widget contract and mirrored assets consistent.
- `agentnexlify-runtime-constraints`: account for multi-worker runtime behavior, background jobs, and in-memory limits.

## Autonomous AI Runtime
- The autonomous development runtime lives in `ai/`.
- Generated reusable skills live in `skills/generated/`.
- The skill index lives in `skills/index.json`.
- Task memory lives in `ai/memory/`.
- For autonomous task preparation, resolution, recording, and self-improvement, use:
  - `python -m ai.skill_engine prepare "..."`
  - `python -m ai.skill_engine complete "..."`
  - `python -m ai.auto_improve --create-skills --write-report docs/ai-auto-improve-report.md --refresh-docs`

## Common Commands
- Backend dev server: `uvicorn backend.main:app --reload --port 8000`
- Frontend dev server: `cd frontend && npm run dev`
- Frontend build: `cd frontend && npm run build`
- Demo platform: `cd demo-platform && npm start`
- Docker stack: `docker compose up --build`

## AI Skills, Agents & Workflows

### Skills (Domain Knowledge Modules)

Skills encode domain expertise and mandatory invariants. Read the relevant skill before working in its area.

**Claude skills** (`.claude/skills/*/SKILL.md`):

| Skill | When to Use |
|-------|-------------|
| `schema-guard` | Before any DB query, migration, or Pydantic model |
| `feature-build` | When building any new feature |
| `debug-api` | When diagnosing API errors (422s, 500s, CORS, silent data loss) |
| `migration-workflow` | When creating, applying, or verifying database migrations |
| `ai-feature-pattern` | When building features that call the Claude API |
| `widget-test` | When testing or modifying the chat widget |
| `industry-content` | When adding support for a new business type/industry |
| `team-orchestration` | When delegating to multiple agents |
| `build-loop` | Autonomous infinite development loop |

**Codex skills** (`.codex/skills/*/SKILL.md`):

| Skill | When to Use |
|-------|-------------|
| `agentnexlify-surface-selector` | Deciding which directory/subsystem to edit |
| `agentnexlify-schema-guard` | Protecting live schema conventions |
| `agentnexlify-runtime-constraints` | Multi-worker runtime behavior, in-memory limits |
| `agentnexlify-widget-integrity` | Preserving production widget contract |

**LLM Council** (`skills/llm-council/SKILL.md`):
- Five independent AI advisors debate complex decisions with real stakes
- Triggered by "council this", "pressure-test this", "war room this"

### Agent Definitions (Specialized Roles)

Located in `.claude/agents/`. Each agent has deep domain knowledge encoded in its markdown file.

| Agent | File | Domain |
|-------|------|--------|
| schema-guardian | `.claude/agents/schema-guardian.md` | Database schema expert — use FIRST |
| backend-dev | `.claude/agents/backend-dev.md` | FastAPI, Pydantic, Supabase, Stripe |
| frontend-dev | `.claude/agents/frontend-dev.md` | React, Vite, Tailwind, dashboard pages |
| widget-specialist | `.claude/agents/widget-specialist.md` | Chat widget, CORS, embedding |
| qa-tester | `.claude/agents/qa-tester.md` | Testing, validation, edge cases |
| devops | `.claude/agents/devops.md` | CI/CD, Railway, Vercel, monitoring |

**Delegation order:** schema-guardian → backend-dev + frontend-dev (parallel) → qa-tester → devops

### Workflows (Step-by-Step Procedures)

Located in `.claude/commands/`. Each workflow is a markdown file with orchestration steps.

| Workflow | Purpose |
|----------|---------|
| `new-feature.md` | Schema → Backend → Frontend → QA → Commit |
| `fix-bug.md` | Check patterns → Diagnose → Fix → Verify → Document |
| `deploy.md` | QA + DevOps in parallel → Fix blockers → Final gate |
| `refactor.md` | Analyze → Plan → Execute incrementally → Verify |
| `delegate.md` | Plan multi-agent delegation for complex tasks |
| `deploy-check.md` | Pre-deploy checklist and validation |
| `health-check.md` | Codebase health check |
| `checkpoint.md` | Save session state for context recovery |
| `recover.md` | Restore context after session restart |
| `summary.md` | Comprehensive change summary with metrics |
| `log-bug.md` | Document a fixed bug for future reference |
| `script.md` | Generate client-ready demo script |

### Agent Communication

Agents coordinate via `.claude/agent-comms/`:
- Each agent writes findings to `{agent-name}-output.md`
- Orchestrator reads outputs and routes to next agent
- Session state saved to `checkpoint.md`

### Workspace Contexts

Each workspace has a `CONTEXT.md` with local rules and patterns:
- `backend/CONTEXT.md` — Backend-specific conventions
- `frontend/CONTEXT.md` — Frontend-specific conventions
- `widget/CONTEXT.md` — Widget-specific conventions
- `planning/CONTEXT.md` — Specs and architecture decisions
- `ops/CONTEXT.md` — Deployment and operations
