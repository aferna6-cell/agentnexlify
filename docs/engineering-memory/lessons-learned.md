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

## 2026-03-23 Session 3

### .get() NULL bug keeps coming back
Session 2 said it fixed all .get("business_name", default) patterns but 15 more were found in files not checked previously. The `or` pattern needs to be enforced project-wide. Files missed last time: dependencies.py, billing.py (Stripe customer creation), auth.py, widget_config.py, widget_chat.py, and several others. **Solution**: grep for `.get("business_name",` before every commit.

### Route shadowing needs automated detection
Added route shadow detection script that found 12 shadowing issues in client_portal.py and 1 in gbp.py. These are all POST /client/register, /client/login etc. being matched by /{tenant_id}/service-records. Fix: separate routers for static vs parameterized paths. Should add this check to pre-commit hook.

### Widget typing indicator already existed
Backlog item "Widget typing indicator" was listed as TODO but showTyping()/hideTyping() with CSS bouncing dot animation was already implemented. Always verify backlog items against actual code before building.
