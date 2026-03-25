# Lessons Learned
_Append-only. Never delete entries. This is institutional memory._

## 2026-03-25 (evening)
- **`or` + `==` operator precedence is a recurring pattern**: Third occurrence found: `tenant.get("business_type") or "".lower() == "restaurant"`. Previous instances: birthday greeting plan check (2026-03-24 night), and several `.get("plan", "free")` vs `.get("plan") or "free"` issues. **Rule: ALWAYS wrap `or` fallbacks in parentheses when comparing the result.** `(x.get("key") or "default") == "value"`, never `x.get("key") or "default" == "value"`.
- **N+1 patterns keep appearing in background tasks**: The scheduled post publisher had the same per-row UPDATE loop that was already fixed in stalled campaign recovery (Cycle 104) and no-response leads dedup (Cycle 82). Background automation tasks are the most common location for N+1 patterns because they process batches by design. **Always batch with `.in_()` when updating multiple rows.**

## 2026-03-25
- **Pre-insert checks + DB constraints = defense in depth**: For appointment double-booking, both the application-level overlap check AND the DB EXCLUDE constraint are needed. The app check catches 99% of cases, the DB constraint catches the race condition. Always handle constraint violations gracefully (409, not 500).
- **Invoice number uniqueness needs retry logic**: Sequential number generation is inherently racy under concurrent requests. The retry-with-increment pattern (try seq N, fail, try N+1) is simpler than distributed locks and works well enough for the volume of invoices a small business generates.
- **HMAC-signed public URLs are the right pattern**: For reschedule links, unsubscribe links, and portal tokens, HMAC signatures verify authenticity without storing tokens in the DB. Use a consistent secret key and include the resource ID in the signature payload.

## 2026-03-24 (night)
- **Python operator precedence with `or` and `==`**: `a.get("x") or "default" == "default"` is NOT the same as `(a.get("x") or "default") == "default"`. The first evaluates as `a.get("x") or ("default" == "default")` which is `a.get("x") or True`, always truthy. Always wrap `or` fallbacks in parentheses when comparing.
- **log_activity positional args are fragile**: The assign_lead code was passing `db` as the first positional arg to log_activity, which silently accepted it as tenant_id (strings and objects are both valid). Use keyword arguments for all log_activity calls to prevent this class of bug.
- **Detached HEAD from previous sessions**: When the previous session commits on detached HEAD, the new session needs to merge those commits back into master before working. Use `git merge <hash>` on master.

## 2026-03-24 (afternoon)
- **dict.get("key", default) returns None for NULL**: When Supabase returns NULL for a column, the key exists in the dict but the value is None. `dict.get("key", "default")` only uses the default when the key is MISSING, not when the value is None. The correct pattern is `dict.get("key") or "default"`. Found 22+ occurrences of this for plan, 40+ for business_name/type/city. This is the most common bug pattern in the codebase.
- **conversations table uses client_id EVERYWHERE**: Not just in the conversation_inbox -- also in sms.py, analytics.py, widget_helpers.py, auth.py, channel_manager.py, etc. Every query on the conversations table must use client_id. Found 6 violations in sms.py and analytics.py this session.
- **Systematic bugs need systematic fixes**: When finding a pattern bug (like .get with default), search the entire codebase instead of fixing just the one instance. Use `grep -rn` to find all occurrences.

## 2026-03-24
- **API client must handle 204 No Content**: The shared `request()` function in `_client.js` was calling `res.json()` on every response, including 204 No Content from DELETE endpoints. This silently broke delete operations across 20+ modules. Fix: check `res.status === 204` and empty body text before parsing.
- **sms_sender vs twilio_service**: The SMS sending function lives in `backend/services/twilio_service.py` (not `sms_sender.py`). Import path: `from backend.services.twilio_service import send_sms`.
- **Python deps not in requirements.txt**: The project has many pip packages not tracked in a requirements file. When cloning fresh, need to install: fastapi, uvicorn, pydantic, pydantic-settings, supabase, httpx, python-jose, python-multipart, slowapi, anthropic, resend, twilio, stripe, python-json-logger, bcrypt, email-validator, google-auth, google-auth-oauthlib, google-api-python-client, cffi, cryptography, mcp, qrcode, pillow.
- **git branch is `master` locally but remote is `main`**: Push with `git push -u origin master:main`.
- **Conversations table uses `client_id` not `tenant_id`**: Verified in conversation_inbox.py `_find_conversation()`. All queries correctly use `.eq("client_id", tenant_id)`.
