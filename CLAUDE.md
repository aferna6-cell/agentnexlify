# AgentNexLiFy — CLAUDE.md

AI-powered business automation platform. Chat widget captures leads, books appointments, and automates follow-ups for small businesses.

## Critical Rules
- Research the codebase before editing. Never change code you haven't read.
- NEVER use `from __future__ import annotations` in any Python file — it breaks FastAPI
- NEVER use localStorage in React artifacts
- Always use `client_id` (not `tenant_id`) when querying the `leads` table
- Always use `status` (not `lead_stage`) for lead status in the `leads` table
- Widget JS must be identical in widget/ AND frontend/public/widget/
- NEVER commit .env files or log secret values
- Database schema changes ONLY via numbered migration files in migrations/
- NEVER use WebFetch or WebSearch — use `agent-browser` via Bash instead

## Operating Rules (behavioral)
- **Caveman mode** output by default — drop filler, fragments OK. See `.claude/rules/caveman-mode.md`
- **UltraPlan + UltraThink** always — extended thinking, plan mode for 2+ files. See `.claude/rules/ultrathink.md`
- **No assumptions** — confidence <80% → ask. See `.claude/rules/no-assumptions.md`
- **Model routing** — Haiku for mechanical, Sonnet for code, Opus for planning. See `.claude/rules/model-routing.md`
- **Parallel approaches** — 2 worktree agents when approach unclear. See `.claude/rules/parallel-approaches.md`
- **Prompt library first** — read `PROMPTLIBRARY.md` before tasks. See `.claude/rules/prompt-library.md`
- **KB first** — check `knowledge-base/wiki/` before researching. See `.claude/rules/kb-first.md`
- **12 usage patterns** — fight-me, interview-first, specific-reader, decision-framework, stress-test, living-doc, build-the-system, etc. See `.claude/rules/claude-usage-patterns.md`
- **Personality** — direct, evidence-first, no preamble/hedging. See `.claude/rules/personality.md`

> Domain-specific rules in `.claude/rules/`: schema-discipline, python-fastapi, frontend-patterns, security-rules, widget-rules, api-conventions, testing-standards, gitnexus, workflow-orchestration, codex-subagents
>
> Behavioral rules in `.claude/rules/`: caveman-mode, model-routing, no-assumptions, parallel-approaches, ultrathink, prompt-library, kb-first, claude-usage-patterns, personality
>
> Security hardening in `.claude/rules/`: claude-code-security (permissions.deny + ask + sandbox config per Trail of Bits-style guide)

## Tech Stack
- Backend: FastAPI, Python 3.11, Pydantic, Supabase Python client
- Frontend: React, Vite, Tailwind-style CSS, Recharts
- Database: Supabase (PostgreSQL with RLS)
- AI: Anthropic Claude API (claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5-20251001)
- Email: Resend | SMS: Twilio | Payments: Stripe
- Hosting: Railway (backend), Vercel (frontend)

## Architecture

```
Browser → Chat Widget (embedded JS) → FastAPI /api/chat → Claude API
                                     → Supabase (messages, leads, appointments)
Dashboard (React/Vite) → FastAPI /api/* → Supabase
```

Widget is tenant-scoped. Every request carries a tenant/client ID. Multi-tenant from day one.

## Key Directories
- `backend/` — FastAPI service (`main.py`, `routers/`, `services/`)
- `frontend/` — React/Vite dashboard (`src/pages/`, `src/utils/api/`)
- `widget/` + `frontend/public/widget/` — Embeddable chat widget (must be identical)
- `migrations/` — SQL migration files (001–096+)
- `docs/dev-knowledge/` — Knowledge base (bug-patterns.md, schema-log.md, architecture-decisions.md)
- `knowledge-base/` — LLM-compiled KB (`raw/`, `wiki/`, pgvector embeddings)
- `_archive/`, `landing-page-v2/`, `public/` — Legacy (do not touch)

## Common Commands
- Frontend dev: `cd frontend && npm run dev`
- Frontend build: `cd frontend && npm run build`
- Backend dev: `uvicorn backend.main:app --reload --port 8000`
- Install git hooks: `bash scripts/install-hooks.sh`

## Plan Names
- free, growth ($249), professional ($499), autopilot ($299), enterprise ($899)
- Old prices (legacy): growth ($199), professional ($399), enterprise ($799)
- Old names (DO NOT USE): foundation, operations

## Automation
- **Pre-commit hook** — blocks secrets, dangerous imports, bare except blocks
- **Pre-push hook** — frontend build + schema consistency check
- **GitHub Actions** — daily health check, PR validation, auto bug logging, AI auto-improve
- **Claude Code hooks** — pre-edit sensitive file warning, post-edit pattern scan, anti-desperation, UltraPlan/UltraThink, 90% confidence gate

## Daily Routine
Automated: 8 AM morning, 8 PM evening (scripts/daily/). Interactive: `/morning`, `/evening`.

## Workflows
- **New API endpoint:** Check routers → schema-guard → Pydantic model → route → register in main.py
- **New dashboard page:** `frontend/src/pages/` → dark theme → live API → helpful empty states → sidebar
- **Database migration:** Next numbered file in `migrations/` → apply via Supabase MCP → update schema-log.md

## Competitive Intel
- GoHighLevel: AI Employee, white-label SaaS, $97-497/mo — #1 competitor
- Drillbit (YC): AI receptionist + quoting + CRM for contractors
- Phonely/Toma (YC): AI receptionists
- Birdeye/Podium: $300-600/mo, AI review responses
- Oscar Chat: $40/mo budget competitor

## Knowledge Base
`docs/dev-knowledge/`: bug-patterns.md, schema-log.md, architecture-decisions.md. Always update after fixing bugs or changing schema.

## Workspaces & Routing

| Task | Go to | Read first |
|------|-------|------------|
| Spec a feature or plan | /planning | CONTEXT.md |
| Backend code | /backend | CONTEXT.md |
| Frontend code | /frontend | CONTEXT.md |
| Widget/knowledge base | /widget | CONTEXT.md |
| Deploy, monitor, docs | /ops | CONTEXT.md |
| Complex decision | /skills/llm-council | SKILL.md |

Workspaces: `/backend`, `/frontend`, `/planning`, `/ops`, `/widget` — each has `CONTEXT.md`.

## Naming Conventions
- Specs: `feature-name_spec.md` (in `/planning/specs/`)
- Decisions: `YYYY-MM-DD-decision-title.md` (in `/planning/decisions/`)
- Knowledge bases: `tenant-name_kb.md` (in `/widget/knowledge-bases/`)

## LLM Council
Triggers: "council this", "pressure-test this", "war room this". Five independent AI advisors in parallel, peer-review, chairman synthesizes. Only for genuine uncertainty with real stakes.
