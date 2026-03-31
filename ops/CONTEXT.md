# Ops Workspace
<!-- Last updated: 2026-03-31 -->

Deployment, infrastructure, monitoring, operational scripts, and documentation for AgentNexLiFy.

## Infrastructure

- **Backend:** Railway (project "cheerful-freedom", service "agentnexlify") — 4 Uvicorn workers
- **Frontend:** Vercel (agentnexlify.com)
- **Database:** Supabase (PostgreSQL with RLS)
- **Widget embed:** Served from Railway (not Vercel)

## Deploy Process

1. Backend: Railway auto-deploys from `main` branch (or manual trigger via Railway dashboard)
2. Frontend: Vercel auto-deploys from `main` branch
3. Widget loads from Railway — if widget breaks externally, check CORS in `backend/main.py`
4. Always verify smoke tests pass after any deployment

## What Happens Here

- Deploy scripts and configuration management
- Environment variable management (Railway and Vercel)
- Monitoring and alerting setup
- Operational scripts (tenant provisioning, data cleanup)
- API documentation, user guides, changelog
- Incident investigation and resolution

## Folders

- `/ops/deploy` — Deploy configs, environment templates
- `/ops/monitoring` — Health checks, alerting rules
- `/ops/scripts` — Operational scripts
- `/ops/docs/api` — API endpoint docs (request/response, auth, errors)
- `/ops/docs/guides` — Setup guides, integration docs, user manuals
- `/ops/docs/changelog` — Release notes by date

## Existing Documentation

- `docs/dev-knowledge/bug-patterns.md` — Known bug patterns and fixes
- `docs/dev-knowledge/schema-log.md` — Schema change history
- `docs/dev-knowledge/architecture-decisions.md` — Architecture decision log
- `docs/ai-development.md` — Automation, hooks, and AI workflow docs
- `docs/scheduled-routines.md` — Morning/evening automation details

## What to Avoid

- Deploying without running smoke tests
- Storing secrets in code — use Railway/Vercel environment variables
- Making infra changes without documenting them
- Letting the changelog fall behind releases
