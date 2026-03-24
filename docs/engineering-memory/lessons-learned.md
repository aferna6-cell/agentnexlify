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

## 2026-03-23 Session 4

### Cannot git clone in sandboxed environment
The sandboxed environment does not have git credentials configured for cloning private repos. Must use GitHub MCP tools (get_file_contents, push_files) to read and write files. This is slower but works. Future sessions should account for this limitation.

### Comments can mislead — always verify code, not comments
Found a comment in sms.py that said "conversations table uses tenant_id" but the actual code correctly used `client_id`. Comments drift from code. When auditing, check the actual queries, not the comments.

## 2026-03-24 Session 5

### Python operator precedence with `or` and `==`
`tenant.get("plan") or "free" == "free"` does NOT mean `(tenant.get("plan") or "free") == "free"`. It means `tenant.get("plan") or ("free" == "free")` which is `tenant.get("plan") or True` — always truthy! This caused birthday greetings and rebook suggestions to skip ALL paid tenants silently. **Solution**: always use parentheses when combining `or` with `==`: `(x or default) == value`.

### New code introduces old bugs — always re-audit
analytics_team.py was written in Session 4 but referenced `created_by` (non-existent column on appointments), used `"completed"` (wrong value for action_items, should be `"done"`), and filtered on `updated_at` (non-existent on action_items). Each of these existed in the original session. **Solution**: cross-reference ALL column names against migrations/schema-log.md when writing new queries.

### .get("key", "default") keeps regressing
Session 3 fixed 15, Session 4 found 0 regressions, but Session 5 found 7 more in files that weren't checked (bids.py, reviews.py, content.py, jobs.py, widget_helpers.py). **Solution**: the grep pattern `\.get\("[^"]+",\s*"` should be run every session. Eventually add to pre-commit hook.

## 2026-03-24 Session 6

### Rebook dedup must key by appointment, not lead
The rebook suggestion dedup used `lead_id` as the dedup key in activity_log, but `lead_id` is nullable on appointments. When NULL, `.eq("lead_id", None)` in Supabase/PostgreSQL never matches (NULL != NULL), so no dedup happened. **Solution**: key dedup by appointment ID (`rebook_sent_{appt_id}`), which is always non-null.

### No-show detection should include pending status
The original no-show detector only checked `status = 'confirmed'`. But appointments that were never confirmed (still pending) past their start time are also no-shows. Both confirmed and pending should be checked.

### Many backlog items get completed but not marked
11 backlog items were unchecked despite being built in sessions 4-5 (team performance, UTM tracking, sentiment analysis, widget chat hours, bulk invoices, lead nurture score). **Solution**: always scan backlog for done-but-unchecked items at session start.

## 2026-03-24 Session 7

### .get("key", default) regression on boolean/int fields with Pydantic
When Supabase returns NULL for a boolean column, `.get("key", False)` returns None (not False). If this None is passed to a Pydantic model field typed as `bool` (not `bool | None`), Pydantic v2 raises a validation error. This crashed the widget config endpoint for proactive_enabled/proactive_delay_seconds when migration 071 wasn't applied. **Solution**: always use `.get("key") or False` for boolean fields and `.get("key") or default` for int fields from Supabase data feeding into non-optional Pydantic models.

### Phone dedup prevents duplicate leads from missed-call text-back
The widget lead capture only deduped by email. Leads from missed-call text-back (phone-only, no email) were creating duplicates every time they texted again. Adding phone dedup after the email dedup check catches this case.

### Automation loop functions must be imported in main.py
Every new function added to automation_engine.py needs to be: (1) added to the import list in main.py, (2) added to the appropriate tick tier, and (3) wrapped in _safe_run(). Missing any step means the function never executes.
