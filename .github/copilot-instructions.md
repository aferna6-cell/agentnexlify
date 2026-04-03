# AgentNexLiFy — GitHub Copilot Instructions

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
                                     → Twilio (SMS notifications)

Dashboard (React/Vite) → FastAPI /api/* → Supabase
```

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `backend/` | FastAPI service (`main.py`, `routers/`, `services/`) |
| `frontend/` | React/Vite dashboard (`src/pages/`, `src/utils/api.js`) |
| `widget/` | Embeddable chat widget (canonical source) |
| `migrations/` | SQL migration files (001-064) |
| `demo-platform/` | Separate demo app (isolated from production) |
| `_archive/`, `landing-page-v2/`, `public/` | Legacy — do not touch |

## AI Resources Available

This repo has extensive AI agent infrastructure. See `.ai/manifest.json` for full discovery.

### Skills (Domain Knowledge Modules)

Read these before working in their domain — they contain invariants and workflows:

| Skill | File | When to Use |
|-------|------|-------------|
| schema-guard | `.claude/skills/schema-guard/SKILL.md` | Before any DB query, migration, or Pydantic model |
| feature-build | `.claude/skills/feature-build/SKILL.md` | When building any new feature |
| debug-api | `.claude/skills/debug-api/SKILL.md` | When diagnosing API errors |
| migration-workflow | `.claude/skills/migration-workflow/SKILL.md` | When creating/applying migrations |
| ai-feature-pattern | `.claude/skills/ai-feature-pattern/SKILL.md` | When building Claude API features |
| widget-test | `.claude/skills/widget-test/SKILL.md` | When testing the chat widget |
| industry-content | `.claude/skills/industry-content/SKILL.md` | When adding new business type support |

### Agent Definitions (Specialized Roles)

Each agent file contains deep domain knowledge for its area:

| Agent | File | Domain |
|-------|------|--------|
| schema-guardian | `.claude/agents/schema-guardian.md` | Database schema |
| backend-dev | `.claude/agents/backend-dev.md` | FastAPI backend |
| frontend-dev | `.claude/agents/frontend-dev.md` | React frontend |
| widget-specialist | `.claude/agents/widget-specialist.md` | Chat widget |
| qa-tester | `.claude/agents/qa-tester.md` | Testing & validation |
| devops | `.claude/agents/devops.md` | Deployment & infra |

### Workflow Templates

Step-by-step procedures for common operations:

| Workflow | File | Purpose |
|----------|------|---------|
| new-feature | `.claude/commands/new-feature.md` | End-to-end feature build |
| fix-bug | `.claude/commands/fix-bug.md` | Bug diagnosis and fix |
| deploy | `.claude/commands/deploy.md` | Pre-deploy validation |
| refactor | `.claude/commands/refactor.md` | Safe incremental refactoring |
| delegate | `.claude/commands/delegate.md` | Multi-agent task delegation |

### Codex Skills (Alternative Format)

Same domain knowledge in Codex-native format:

| Skill | File |
|-------|------|
| surface-selector | `.codex/skills/agentnexlify-surface-selector/SKILL.md` |
| schema-guard | `.codex/skills/agentnexlify-schema-guard/SKILL.md` |
| runtime-constraints | `.codex/skills/agentnexlify-runtime-constraints/SKILL.md` |
| widget-integrity | `.codex/skills/agentnexlify-widget-integrity/SKILL.md` |

## Schema Gotchas

- `leads` table uses `client_id` for tenant linkage (all other tables use `tenant_id`)
- `conversations` table also uses `client_id`
- Lead status column is `status` (not `lead_stage` — that column never existed)
- Lead interest column is `areas_of_interest` (not `service_interest` — never existed)
- `chat_messages` is the active message store (not `conversations.messages`)
- Auth uses `tenant_id` in JWTs

## Common Commands

```bash
uvicorn backend.main:app --reload --port 8000   # Backend dev
cd frontend && npm run dev                        # Frontend dev
cd frontend && npm run build                      # Frontend build
```

## Full Documentation

- **`CLAUDE.md`** — Comprehensive project rules, full schema, all conventions
- **`AGENTS.md`** — Repository guide with subsystem map and invariants
- **`.ai/manifest.json`** — Machine-readable manifest of all AI resources
- **`docs/dev-knowledge/`** — Bug patterns, schema log, architecture decisions
