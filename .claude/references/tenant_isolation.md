# Tenant Isolation — Reference Pack

Load before any DB query, migration, Pydantic model, or API endpoint.

## Column Discipline

| Table | Tenant column |
|-------|---------------|
| `leads` | `client_id` (NOT `tenant_id`) |
| `conversations` | `client_id` (NOT `tenant_id`) |
| `messages` | joined via conversation |
| `appointments` | `client_id` |
| `clients` | `id` (this is the tenant itself) |

**Rule:** Shipped production bugs 3+ times from `tenant_id` vs `client_id` drift. `client_id` always wins on leads and conversations.

## Lead Schema Gotchas

| Wrong | Right |
|-------|-------|
| `lead_stage` | `status` |
| `service_interest` | `areas_of_interest` |
| `tenant_id` | `client_id` |

These columns never existed under the wrong names. If you see `lead_stage` in code, it's a bug.

## RLS Scope

Every table with tenant data has RLS policies scoping by `client_id = auth.uid()` or service-role bypass.

**Required:**
- Every SELECT includes tenant filter — never `SELECT * FROM leads` unscoped
- Service-role queries log intent so tenant access is auditable
- New tables inherit RLS policy from `migrations/RLS_template.sql` pattern
- Cross-tenant queries require explicit admin context

## FastAPI Route Contract

**Required:**
- Every route that touches tenant data depends on `get_current_client()` or equivalent
- `client_id` always comes from auth context, never from request body/query
- Unit tests assert cross-tenant isolation (tenant A cannot read tenant B)

**Forbidden:**
- `client_id` in query params for read endpoints (auth context only)
- Trusting request body `client_id` without re-verification
- Caching responses without tenant-key prefix

## Pydantic Model Contract

```python
class Lead(BaseModel):
    id: str
    client_id: str  # NEVER tenant_id
    status: str     # NEVER lead_stage
    areas_of_interest: list[str]  # NEVER service_interest
```

Model field names MUST match DB columns. Pydantic serialization breaks silently when they diverge.

## Testing Isolation

Every new endpoint gets two tests:
1. Happy path — tenant A reads own data → 200
2. Isolation — tenant A reads tenant B's data → 404 (not 403, no leakage)

## Anti-patterns

- Never write an un-scoped query "just for now"
- Never accept `client_id` from request body on a read endpoint
- Never disable RLS for convenience in local dev — use service role with explicit scope
- Never add a new table without RLS + tenant column + migration
- Never rename `client_id` → `tenant_id` "for consistency" — 15+ call sites break

## Cross-refs

- `CLAUDE.md` — Critical invariants #1, #2, #3
- `.claude/rules/schema-discipline.md`
- `.claude/agents/schema-guardian.md`
- `migrations/` — RLS policy patterns
- `backend/CONTEXT.md`
