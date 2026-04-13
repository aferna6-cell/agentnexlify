---
description: Codebase audit. Use when user says health check, audit the code, or before a major release.
model: sonnet
---

Perform a health check on the AgentNexLiFy codebase. Check for:

1. Schema mismatches: Compare Pydantic models against migration files. Flag any column name in code but not in the latest migration.
2. Dead imports: Look for imports in backend routers and main.py that reference nonexistent modules.
3. Silent exception handling: Find bare `except: pass` patterns that swallow errors.
4. `from __future__ import annotations`: Flag if in ANY backend router file.
5. Unregistered routes: Check every router file in backend/routers/ is registered in backend/main.py.
6. Frontend stale references: Check for frontend API calls in frontend/src/utils/api.js referencing undefined backend endpoints.
7. CORS completeness: Check if any frontend deployment URLs are missing from the CORS allowlist in backend/main.py.
8. Migration numbering: Check for duplicate or out-of-sequence migration numbers in migrations/.
9. Widget sync: Verify widget/agentnexlify-widget.js matches frontend/public/widget/agentnexlify-widget.js.
10. Leads table: Verify all leads queries use `client_id` (not `tenant_id`) and `status` (not `lead_stage`).

Output a markdown report grouped by severity (Critical / Warning / Info). Save to docs/dev-knowledge/health-check-latest.md.
