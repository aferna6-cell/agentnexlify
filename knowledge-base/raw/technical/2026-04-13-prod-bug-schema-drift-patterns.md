---
title: Production bug patterns from Railway logs (2026-04-13)
date: 2026-04-13
source: railway deploy logs + in-repo fix (commit cc7e1f8)
category: technical
tags: [supabase, pydantic, schema-drift, fastapi, debugging]
---

# Production Bug Patterns — 2026-04-13 Railway Logs

Two high-frequency latent bugs surfaced by filtering Railway deploy logs
with `@level:error`. Both passed pytest because test mocks masked the
live schema reality. Both fixed in commit `cc7e1f8`.

## Pattern 1 — Querying a dropped column

**Symptom.** On every new widget lead, `backend/services/lead_scoring.py`
raised `postgrest.exceptions.APIError: column conversations.messages does
not exist` (PostgreSQL `42703`). Scoring was swallowed at the `except`
boundary, so the dashboard kept rendering — the lead just never got
scored.

**Root cause.** `conversations.messages` was a JSONB column in the
original schema. A later reconciliation migration dropped it without
updating consumers. The canonical message store is the `chat_messages`
table (`migrations/006_chat_messages.sql`), keyed by `tenant_id +
session_id + created_at`. Widget, SMS, Twilio, and calls all write
there via `backend/routers/widget_helpers._save_chat_messages`.

**Fix.** Replace `conversations.select("messages, last_message_at")`
with a two-step read:

```python
conv_result = (
    db.table("conversations")
    .select("session_id, last_message_at")
    .eq("id", conv_id)
    .limit(1)
    .execute()
)
# Then, if we got a session_id, pull from chat_messages:
msg_result = (
    db.table("chat_messages")
    .select("role, content, created_at")
    .eq("tenant_id", tenant_id)
    .eq("session_id", session_id)
    .order("created_at")
    .execute()
)
```

**General lesson.** When the live schema drifts from original migrations,
pytest alone won't catch it if your mocks return the old shape. Two
defenses:

1. A pre-commit grep that blocks future `.select("...messages...")` on
   the `conversations` table (added to
   `scripts/hooks/pre-commit` CHECK 8).
2. Periodic `@level:error` passes over Railway deploy logs — the fast
   way to surface schema drift without touching production SQL.

## Pattern 2 — `dict.get(key, default)` vs. explicit `None`

**Symptom.** Dashboard widget for needs-attention leads silently
returned an empty list. Railway log showed:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for
ClientListItem lead_score
  Input should be a valid integer [type=int_type, input_value=None]
```

**Root cause.** The codepath built `ClientListItem(lead_score=l.get(
"lead_score", 0))`. `dict.get(key, default)` only returns `default`
when the key is **missing**. When the DB row contains `{"lead_score":
None}` (the common state before a lead has been scored), `.get`
returns `None`. The Pydantic model declared `lead_score: int = 0`,
with no `| None`, so validation rejected `None` and the endpoint
raised.

**Fix.** Use `row.get(key) or 0` — coerces both missing and explicit
`None` to `0`:

```python
lead_score=l.get("lead_score") or 0,
```

Applied at 4 sites across `backend/routers/clients.py`,
`backend/mcp_server.py`.

**General lesson.** Anywhere a nullable Supabase integer column feeds a
Pydantic `int` field, never rely on `dict.get(key, default)`. This
bug pattern also applies to counts, scores, ratings, and any column
that starts null and gets populated on a later event. Either:

- Coerce at the boundary: `row.get(key) or 0`
- Widen the Pydantic type: `lead_score: int | None = None`
- Use a Pydantic `@field_validator` to coerce `None → 0`

## Why pytest missed both

The repo's `_mock_db` fixtures in `tests/test_quick_fixes.py` returned
the old `conversations.messages` shape, so tests for lead scoring ran
against a schema that no longer exists. Fixed the mock in the same
commit so future regressions do surface in CI.

For lead_score, there was no test exercising a freshly-inserted lead
with `lead_score = None`. Add one if you touch this area again.

## References

- Commit: `cc7e1f8` on `main`
- Bug log entries: `docs/dev-knowledge/bug-patterns.md` (top of file)
- Railway filter used: `railway logs --filter '@level:error' --lines 100`
- Canonical schema reference: `.claude/rules/schema-discipline.md`
