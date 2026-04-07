---
name: feature-build
description: "Use this skill when building any new feature. Ensures schema safety, consistent patterns, and proper documentation."
version: 1.0.0
origin: claude
allowed_tools: []
triggers: ["new feature", "new API endpoint", "new dashboard page", "new integration", "build feature", "feature build"]
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
