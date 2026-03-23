# Lessons Learned
_Append-only. Never delete entries. This is institutional memory._

## 2026-03-23

### conversations table client_id is an endless regression
The conversations table uses `client_id` not `tenant_id`. This has been fixed 5 separate times across different files. Each time, new code gets written with `tenant_id` because every other table uses that name. **Solution needed**: a pre-commit hook that greps for `conversations.*tenant_id` in Python files.

### Route shadowing is a systemic pattern
FastAPI route shadowing (static paths after parameterized paths) has occurred 4 times: invoices.py, forms.py, documents.py, webhooks.py. **Solution needed**: automated check in pre-commit hook or a code review checklist item.

### dict.get() with Supabase NULL values
`dict.get("key", default)` does NOT return the default when Supabase returns NULL — it returns None. Must use `dict.get("key") or default` instead. This affected 36+ locations across the codebase.

### Run automated bug-pattern checks before building new features
The systematic code audit found 48 individual bugs across 13 files. These were all latent bugs that had been introduced over many sessions. Phase A (bug hunt) before Phase B (new features) is critical.
