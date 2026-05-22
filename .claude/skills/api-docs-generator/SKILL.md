---
name: api-docs-generator
effort: medium
description: Extract FastAPI OpenAPI schema and produce human-readable markdown docs with examples, error codes, and auth. Output to docs/api/. Load when user says "generate API docs", "document the API", "openapi to markdown", "API reference for X".
origin: inspired by ComposioHQ/awesome-claude-skills/api-docs-generator
version: 1.0.0
triggers:
  - generate API docs
  - document the API
  - openapi to markdown
  - API reference for
  - extract API docs
  - swagger to markdown
---

# API Docs Generator — FastAPI → Markdown

FastAPI auto-generates OpenAPI at `/openapi.json`. This skill turns it into reviewable markdown with examples, error codes, auth notes, and tenant scope.

## When to Use
- New router added → docs need refresh
- Customer-facing API doc snapshot for a release
- Auditing endpoint surface (security review)
- Producing reference for partner integrations
- Generating Postman/Insomnia collections

## When NOT to Use
- Single-endpoint quick reference (just read the router file)
- Internal-only debug endpoints (don't publish)
- Generation already done this session (don't regenerate noise)

## Inputs
- Live backend at `localhost:8000` OR static `openapi.json` export
- `backend/routers/*.py` for source-of-truth examples
- `backend/dependencies.py` for auth requirements

## Process
1. **Start backend** (if not running): `python -m uvicorn backend.main:app --reload --port 8000`
2. **Fetch schema**: `curl -s http://localhost:8000/openapi.json > /tmp/openapi.json`
3. **Group endpoints** by router/tag
4. **Per endpoint**: extract method, path, params, request schema, response schema, auth, error codes
5. **Add real examples** from router source (find a working request in tests or logs)
6. **Note tenant scope** — mark `requires X-Client-Id`, `service-role only`, etc.
7. **Output** to `docs/api/<router-name>.md`
8. **Update index** at `docs/api/README.md`

## Output template per endpoint
```markdown
### `POST /api/leads`

**Auth:** Bearer JWT (tenant operator) + `X-Client-Id` header
**Tenant scope:** scoped to `client_id` from header
**Idempotency:** none (creates new row each call)

#### Request
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+15551234567",
  "areas_of_interest": ["plumbing", "leak"],
  "source": "widget",
  "conversation_id": "uuid-here"
}
```

#### Response 201
```json
{
  "id": "uuid",
  "client_id": "tenant-uuid",
  "status": "new",
  "created_at": "2026-04-15T12:00:00Z"
}
```

#### Errors
| Code | When | Body |
|---|---|---|
| 400 | Invalid email/phone | `{"detail": "Invalid phone format"}` |
| 401 | Missing/expired JWT | `{"detail": "Not authenticated"}` |
| 403 | client_id mismatch | `{"detail": "Tenant access denied"}` |
| 422 | Pydantic validation | `{"detail": [...]}` |
| 500 | DB unavailable | `{"detail": "Internal error"}` |

#### Notes
- Column is `client_id` (NEVER `tenant_id`) — see `.claude/rules/schema-discipline.md`
- Status is `status` (NEVER `lead_stage`)
- Areas tagged is `areas_of_interest` (NEVER `service_interest`)

#### Source
- Router: `backend/routers/leads.py:42`
- Model: `backend/models/lead.py:18`
- Test: `backend/tests/test_leads.py::test_create_lead`
```

## Index (`docs/api/README.md`)
```markdown
# AgentNexLiFy API Reference

Auto-generated from FastAPI OpenAPI schema. Last regenerated: YYYY-MM-DD.

## Routers
- [Leads](./leads.md) — lead capture + management
- [Conversations](./conversations.md) — chat session CRUD
- [Appointments](./appointments.md) — booking flow
- [Subscriptions](./subscriptions.md) — Stripe billing
- [Widget](./widget.md) — public widget endpoints
- [Webhooks](./webhooks.md) — Stripe / Twilio / Resend handlers

## Auth Modes
- Tenant operator JWT (most endpoints)
- Service-role JWT (admin)
- Public (widget endpoints, with rate limits)
- Webhook signature (Stripe/Twilio/Resend)

## Headers
- `Authorization: Bearer <jwt>` — operator
- `X-Client-Id: <uuid>` — tenant scope (always required for tenant ops)
- `Stripe-Signature: <sig>` — Stripe webhook
```

## Constraints
- DO NOT include endpoints flagged `internal_only` or `_debug` in output
- DO NOT publish API keys, webhook secrets, or example tokens that look real
- DO confirm each example matches a passing test before publishing
- DO note rate limits where applicable (`Retry-After` header)

## Verification before publish
```bash
# Lint generated markdown
markdownlint docs/api/*.md

# Sanity check examples — none of these should appear
grep -r "sk_live_" docs/api/
grep -r "whsec_" docs/api/
grep -r "TODO" docs/api/
```

## Cross-refs
- FastAPI source: `backend/routers/`
- Models: `backend/models/`
- Tests: `backend/tests/`
- `.claude/rules/api-conventions.md` — endpoint naming + auth conventions
- `PROMPTLIBRARY.md` — WRITE Documentation prompt
