---
name: feature-build
description: "Use this skill when building any new feature. Ensures schema safety, consistent patterns, and proper documentation."
version: 1.0.0
origin: claude
allowed-tools: []
triggers: ["new feature", "new API endpoint", "new dashboard page", "new integration", "build feature", "feature build"]
effort: high
---

# Feature Build

## When to Use
- Adding a new API endpoint or dashboard page
- Adding a new integration
- Extending an existing feature

## When NOT to Use
- Simple bug fixes that don't add new endpoints or pages
- Configuration-only changes (env vars, deploy settings)
- Refactoring existing code without adding new surface area
- Data migrations that don't touch API or UI

## Pre-Build Checklist
- [ ] Identify which database tables this feature touches
- [ ] Run schema-guard skill to verify column names
- [ ] Check if a similar pattern already exists in the codebase
- [ ] Determine if a database migration is needed

## Backend (FastAPI)
1. Create/update Pydantic models — field names MUST match database columns
2. Create router with try/except and logging on all DB calls
3. Never use `from __future__ import annotations` in router files
4. Register router in main.py if new file
5. Create numbered migration if schema changes needed — check `migrations/` for the current highest number and use next. Use the `migration-workflow` skill.
6. Remember: leads table uses `client_id`, all other tables use `tenant_id`

## Frontend (React/Vite)
1. Create page in frontend/src/pages/
2. Match dark theme from existing dashboard pages
3. Fetch from API on mount — never trust JWT for display
4. Include loading states and helpful empty states
5. Add sidebar navigation link
6. Use frontend/src/utils/api.js for API calls

## Post-Build
- [ ] Test happy path end-to-end
- [ ] Test with missing/invalid data
- [ ] Verify no console errors
- [ ] Update docs/dev-knowledge/schema-log.md if schema changed
- [ ] Update CLAUDE.md if new table added

## Gotchas
- **`from __future__ import annotations`** in any router file → every request 422s. Zero tolerance.
- **Static routes before dynamic routes.** `/templates` must be registered before `/{id}`. FastAPI matches in registration order.
- **`tenant_id` vs `client_id`.** Leads and conversations tables use `client_id`. Everything else uses `tenant_id`. Always route through `backend/services/tenant_scope.py` helpers.
- **In-memory state is per-process only.** Production runs 4 Uvicorn workers. A cache hit in one worker is a miss in another. Use Supabase for anything that needs to survive a worker restart.
- **Pydantic response model mismatch → 500.** If the function returns extra keys and `response_model` is set, FastAPI raises. Always validate the response shape matches the model.
- **Dark theme only.** New frontend pages must match the existing dashboard dark theme. See `design.md`.
- **Display data from stale JWT.** Never render plan/email from `user` — fetch live from `/api/v1/dashboard`. JWT claims don't refresh on plan change.
- **Migration file created but never applied.** See `migration-workflow` skill — file existing ≠ column existing in prod. Use Supabase MCP or Management API after creating.
- **Widget must stay in sync.** `widget/` and `frontend/public/widget/` must be byte-identical. Pre-push hook enforces, but still easy to miss.
- **Adding a new table ≠ adding to CLAUDE.md.** Update the schema table in CLAUDE.md or future sessions won't know about the new table.
