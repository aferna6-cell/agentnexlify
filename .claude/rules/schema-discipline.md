---
paths:
  - "backend/**/*.py"
  - "migrations/**/*.sql"
---

# Schema Discipline

ALWAYS check the actual Supabase schema before writing queries. Known past issues:
- `client_id` is correct for leads table (NOT `tenant_id`)
- `status` is correct for lead status (NOT `lead_stage`)
- `areas_of_interest` is correct for leads (NOT `service_interest` — that column never existed)
- `conversations` table uses `client_id` (NOT `tenant_id`) — same as leads
- Foreign keys pointing to renamed/dropped tables
- `password_hash` and `owner_name` added in migration 002

**Why:** We've had multiple production bugs from querying non-existent columns. The leads table is the #1 offender — it uses `client_id` everywhere other tables use `tenant_id`.

Before writing any database query, verify the column exists. When creating a migration, check it doesn't conflict with existing schema.

## Migration Rules
- Migration SQL files do NOT auto-apply
- After creating a migration, apply via Supabase MCP (`mcp__supabase__apply_migration`) or SQL editor
- Always flag new migrations in commit messages and update schema-log.md
- Next migration number: check `ls migrations/` for the highest number
- Use `tenant_scope.py` helpers (`tenant_select`, `tenant_table`, `tenant_insert`) — they handle the client_id/tenant_id mapping automatically

## Key Schema Reference (Most-Used Tables)

| Table | Tenant Column | Key Gotchas |
|-------|--------------|-------------|
| leads | `client_id` | NOT tenant_id. Status field is `status`, not `lead_stage` |
| conversations | `client_id` | NOT tenant_id. Same pattern as leads |
| appointments | `tenant_id` | Has EXCLUDE constraint preventing double-booking |
| chat_messages | `tenant_id` | Canonical message store, not conversations.messages |
| documents | `tenant_id` | signing_token used for public access |
| invoices | `tenant_id` | invoice_number is unique per tenant |

> Full schema: see Database Schema section in docs or query Supabase directly
