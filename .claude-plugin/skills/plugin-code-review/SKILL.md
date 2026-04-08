---
name: agentnexlify-review
description: "Code review for AgentNexLiFy multi-tenant SaaS. Checks tenant isolation, route shadowing, schema correctness, and security patterns."
effort: high
allowed-tools: Read, Grep, Glob
---

# AgentNexLiFy Code Review

Review code changes against these critical rules:

## Tenant Isolation
- Every query on `leads` or `conversations` MUST use `client_id` (NOT `tenant_id`)
- All other tenant-scoped tables use `tenant_id`
- Use `tenant_select()`, `tenant_table()`, `tenant_insert()` from `backend/services/tenant_scope.py`
- Every authenticated endpoint MUST call `verify_tenant(claims, tenant_id)` or equivalent

## Route Safety
- Static routes (e.g., `/templates`, `/stats`) MUST be registered BEFORE param routes (e.g., `/{id}`)
- FastAPI matches routes in registration order — param routes capture static path segments

## Schema Correctness
- `status` not `lead_stage` on leads table
- `areas_of_interest` not `service_interest` on leads table
- `client_id` not `tenant_id` on leads and conversations tables

## Error Handling
- No bare `except: pass` — always log with `exc_info=True`
- Guard `.data[0]` access with `if not result.data` check
- Async functions must be awaited or wrapped in `safe_create_task()`

## Security
- Never log secret values
- Never commit .env files
- Validate all user input via Pydantic models
- Never use `from __future__ import annotations` in FastAPI router files
