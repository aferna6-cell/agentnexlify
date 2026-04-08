---
name: agentnexlify-tenant-check
description: "Verify tenant isolation in database queries. Use before committing changes that touch DB queries."
effort: medium
allowed-tools: Read, Grep, Glob
---

# Tenant Isolation Verification

Scan modified files for database queries missing tenant filtering.

## Check Pattern
For each `.table("X").select(...)` call:
1. Identify the table name
2. Look up the correct tenant column: `client_id` for leads/conversations, `tenant_id` for everything else
3. Verify the query chain includes `.eq("tenant_column", tenant_id)`
4. Exception: public endpoints (booking page, document signing) that use token-based auth instead

## Known Overrides
- `tenant_select()`, `tenant_table()`, `tenant_insert()` from `backend/services/tenant_scope.py` handle this automatically
- Booking page uses `_verify_reschedule_token()` for auth
- Document signing uses `signing_token` for auth

## Output
List any queries missing tenant filtering with file, line number, and recommended fix.
