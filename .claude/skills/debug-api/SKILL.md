---
name: debug-api
description: "Use this skill when diagnosing any API error — 422s, 500s, CORS failures, silent data loss, or webhook issues."
version: 1.0.0
origin: claude
allowed_tools: []
triggers: ["422 error", "500 error", "API error", "CORS error", "webhook issue", "silent data loss", "debug API", "API not working"]
effort: high
---

# Debug API

## When to Use
- Any 4xx or 5xx error from the FastAPI backend
- Widget not saving data
- Stripe webhooks not updating the database
- CORS errors in browser console

## When NOT to Use
- Frontend-only bugs with no API involvement
- Database connection or infrastructure issues (check Railway/logs directly)
- Authentication errors caused by expired tokens (check client-side token handling)
- Performance issues that are not errors (use profiling tools instead)

## Diagnostic Workflow

### Step 1: Identify the Error Class

| Symptom | Likely Cause | Start Here |
|---------|-------------|------------|
| 422 Unprocessable Entity | Pydantic model mismatch OR `from __future__ import annotations` | Check the route's request model |
| 500 Internal Server Error | Unhandled exception | Check Railway logs |
| CORS error in browser | Origin not in allowed list | Check main.py CORS config |
| Data silently not saved | Schema mismatch or swallowed exception | Use schema-guard skill |
| Webhook fires but DB unchanged | No error logging in handler | Add try/except with logging |
| Chat sessions not appearing in inbox | Orphaned sessions — chat_messages rows with no matching conversations row | Check for sessions missing from conversations table; backfill or use INSERT ... ON CONFLICT DO NOTHING |
| RLS enabled but writes silently fail | RLS policies missing on table | Check pg_policies for the table; add policies or use service_role key |

### Step 2: Gotchas (known production killers)

- `from __future__ import annotations` in ANY file with FastAPI routes → every request 422s. Deferred annotations make FastAPI treat body models as strings.
- Bare `except: pass` silently swallows the real error. Replace with `except Exception: logger.exception(...)` before debugging further.
- Display data sourced from stale JWT claims (old plan, old email) → UI shows outdated values. Always fetch live from `/api/v1/dashboard` for plan/email fields.
- Leads queries using `tenant_id` instead of `client_id`, or `lead_stage` instead of `status` → silent zero-row returns, not errors.
- CORS preflight returning 400 on third-party domains → widget script dies with "sorry I'm having trouble connecting". Hard-code `allow_origins=["*"]` for the widget (`backend/main.py`). Regression history: fd24b43, 9b07a59.
- Webhook 500s that disappear in prod logs → Railway log tail only shows the last N lines; use `railway logs --deployment <id>` for a full dump.

### Step 3: Trace the Full Request Path
1. Frontend — exact fetch call and payload shape (check frontend/src/utils/api.js)
2. CORS — is the origin allowed? (check backend/main.py)
3. Route — URL and method correct? (check backend/routers/)
4. Pydantic model — request body matches model?
5. Database query — column names match schema?
6. Response — response model correct?

### Step 4: Document the Fix
Append to docs/dev-knowledge/bug-patterns.md with symptom, root cause, fix, and files changed.
