# AgentNexLiFy — Gemini Instructions

AI-powered business automation platform. Chat widget captures leads, books appointments, and automates follow-ups for small businesses.

## Critical Rules

- NEVER use `from __future__ import annotations` in any Python file — breaks FastAPI Pydantic model resolution, causes 422 errors
- Always use `client_id` (not `tenant_id`) when querying the `leads` or `conversations` table
- Always use `status` (not `lead_stage`) for lead status in the `leads` table
- Widget JS in `widget/` and `frontend/public/widget/` must be identical
- Database schema changes ONLY via numbered migration files in `migrations/`
- NEVER commit `.env` files or log secret values
- Production runs with 4 Uvicorn workers — in-memory state is per-process only
- Current plan names: free, growth, professional, autopilot, enterprise
- All tenant-specific queries MUST use RLS or explicit tenant_id/client_id filtering
- Valid Claude API model IDs: claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5-20251001

## Tech Stack

- **Backend:** FastAPI, Python 3.11, Pydantic, Supabase Python client
- **Frontend:** React, Vite, Tailwind CSS, Recharts
- **Database:** Supabase (PostgreSQL with RLS)
- **AI:** Anthropic Claude API (`claude-sonnet-4-6`)
- **Email:** Resend | **SMS:** Twilio | **Payments:** Stripe
- **Hosting:** Railway (backend), Vercel (frontend)

## Architecture

```
Browser → Chat Widget (embedded JS) → FastAPI /api/chat → Claude API
                                     → Supabase (messages, leads, appointments)
Dashboard (React/Vite) → FastAPI /api/* → Supabase
```

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `backend/` | FastAPI service (`main.py`, `routers/`, `services/`) |
| `frontend/` | React/Vite dashboard (`src/pages/`, `src/utils/api.js`) |
| `widget/` | Embeddable chat widget (canonical source) |
| `migrations/` | SQL migration files (001-064) |
| `_archive/`, `landing-page-v2/`, `public/` | Legacy — do not touch |

## Schema Gotchas

- `leads` uses `client_id` for tenant linkage (all other tables use `tenant_id`)
- `conversations` also uses `client_id`
- Lead status: `status` (never `lead_stage`)
- Lead interest: `areas_of_interest` (never `service_interest`)
- `chat_messages` is the active message store
- Auth uses `tenant_id` in JWTs

## AI Agent Infrastructure

This repo has extensive AI-assisted development infrastructure. See `.ai/manifest.json` for the complete machine-readable index of all resources.

### Skills — Domain knowledge modules (read before working in their area)

Located in `.claude/skills/` (SKILL.md files with YAML frontmatter):

| Skill | Trigger |
|-------|---------|
| `schema-guard` | Before any DB query, migration, or Pydantic model |
| `feature-build` | When building any new feature |
| `debug-api` | When diagnosing API errors (422s, 500s, CORS) |
| `migration-workflow` | When creating, applying, or verifying migrations |
| `ai-feature-pattern` | When building features that call the Claude API |
| `widget-test` | When testing or modifying the chat widget |
| `industry-content` | When adding support for a new business type |
| `team-orchestration` | When coordinating multi-agent work |
| `build-loop` | For autonomous continuous development |

Additional Codex-format skills in `.codex/skills/`:
- `agentnexlify-surface-selector` — Choose correct surface before editing
- `agentnexlify-schema-guard` — Schema convention protection
- `agentnexlify-runtime-constraints` — Multi-worker runtime awareness
- `agentnexlify-widget-integrity` — Widget contract preservation

### Agent Definitions — Specialized roles with deep domain knowledge

Located in `.claude/agents/` (Markdown with YAML frontmatter):

| Agent | Domain |
|-------|--------|
| `schema-guardian` | Database schema expert |
| `backend-dev` | FastAPI backend (endpoints, models, queries, Stripe) |
| `frontend-dev` | React/Vite frontend (pages, components, styling) |
| `widget-specialist` | Chat widget (behavior, CORS, embedding) |
| `qa-tester` | Testing and validation |
| `devops` | Deployment, CI/CD, Railway, Vercel |

Delegation order: schema-guardian → backend-dev + frontend-dev (parallel) → qa-tester → devops

### Workflows — Step-by-step procedures

Located in `.claude/commands/` (Markdown files):

| Workflow | Purpose |
|----------|---------|
| `new-feature` | End-to-end feature build pipeline |
| `fix-bug` | Diagnosis → fix → verify → document |
| `deploy` | Pre-deploy validation |
| `refactor` | Safe incremental refactoring |
| `delegate` | Multi-agent task delegation |
| `health-check` | Codebase health check |

### LLM Council — Complex decision framework

Located in `skills/llm-council/SKILL.md`. Five independent AI advisors debate complex decisions. Triggered by "council this" or "pressure-test this" style requests.

## Workspace Contexts

Each workspace has a `CONTEXT.md` with local rules and patterns:
- `backend/CONTEXT.md` — Backend-specific patterns
- `frontend/CONTEXT.md` — Frontend-specific patterns
- `widget/CONTEXT.md` — Widget-specific patterns
- `planning/CONTEXT.md` — Planning and specs
- `ops/CONTEXT.md` — Operations and deployment

## Common Commands

```bash
uvicorn backend.main:app --reload --port 8000   # Backend dev
cd frontend && npm run dev                        # Frontend dev
cd frontend && npm run build                      # Frontend build
```

## Full Documentation

- **`CLAUDE.md`** — Complete project rules, full database schema (40+ tables), all conventions
- **`AGENTS.md`** — Repository guide with subsystem map and invariants
- **`.ai/manifest.json`** — Machine-readable manifest of all AI resources
- **`docs/dev-knowledge/`** — Bug patterns, schema log, architecture decisions
