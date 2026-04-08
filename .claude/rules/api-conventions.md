---
paths:
  - "backend/routers/**/*.py"
---

# API Conventions

## New Endpoint Workflow
Check existing routers → run schema-guard → create Pydantic model → write route → register in main.py

## Patterns
- All routes use `verify_tenant(claims, tenant_id)` or equivalent inline check
- Use `tenant_select()`, `tenant_table()`, `tenant_insert()` from `backend/services/tenant_scope.py` — they handle client_id/tenant_id mapping
- Static routes (e.g., `/templates`, `/stats`) MUST be registered BEFORE param routes (e.g., `/{id}`) to avoid route shadowing. **Why:** FastAPI matches routes in registration order — a param route captures static path segments.
- All endpoints need input validation and proper error responses
- Use `logger.exception()` or `logger.warning(exc_info=True)` in except blocks, never bare `pass`
