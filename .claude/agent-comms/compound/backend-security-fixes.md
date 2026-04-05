# Backend Security/Quality Fixes -- Implementation Summary

## What was done

Four independent security and quality issues identified by audit were fixed across 5 files (config.py + 4 routers).

### 1. Dedicated billing secret (config.py + billing.py)
- Added `billing_secret: str = ""` field to `Settings` in `backend/config.py` (line 52)
- Updated `_verify_secret()` in `backend/routers/billing.py` to prefer `BILLING_SECRET` env var when set, falling back to `api_secret_key` for dev backwards-compat
- **Why:** Separates billing auth from general API auth. Production can set a distinct `BILLING_SECRET` env var; dev environments keep working without any config change.

### 2. Search input sanitization (snippets.py)
- Stripped `,`, `.`, `%`, `_` characters and whitespace from the `search` parameter before injecting into the PostgREST `or_()` filter in `backend/routers/snippets.py`
- Added guard so empty-after-sanitization search is skipped entirely
- **Why:** The PostgREST filter DSL uses `,` and `.` as structural delimiters. A crafted search string like `%,id.eq.` could inject additional filter conditions. Sanitization closes this vector.

### 3. Misleading comment fix (sms.py)
- Changed comment on line 184 from "conversations table uses tenant_id" to "conversations table uses client_id"
- **Why:** The conversations table actually uses `client_id` (same as leads). The misleading comment could cause future developers to write incorrect queries.

### 4. Hardcoded URL replaced (client_portal.py)
- Replaced 2 occurrences of `"https://agentnexlify-production.up.railway.app"` with `settings.api_url` in `backend/routers/client_portal.py` (lines 439 and 751)
- The `from backend.config import settings` import already existed (line 13), so no new import was needed
- **Why:** Hardcoded URLs break in non-production environments (staging, local dev). `settings.api_url` reads from the `API_URL` env var with the production URL as default.

## Files modified
- `/home/aidan/agentnexlify/backend/config.py` -- added `billing_secret` field
- `/home/aidan/agentnexlify/backend/routers/billing.py` -- updated `_verify_secret()` to use billing_secret
- `/home/aidan/agentnexlify/backend/routers/snippets.py` -- sanitized search input
- `/home/aidan/agentnexlify/backend/routers/sms.py` -- fixed misleading comment
- `/home/aidan/agentnexlify/backend/routers/client_portal.py` -- replaced hardcoded URL (2 occurrences)

## Endpoints added/changed
- None added. `_verify_secret` in billing.py now checks `billing_secret` first.

## Models created/changed
- `Settings` in config.py: added `billing_secret: str = ""`

## Migrations needed
- No

## Testing notes
- All 5 files pass `py_compile` syntax check
- Billing: set `BILLING_SECRET=test123` env var, verify billing endpoints accept `test123` and reject the old api_secret_key. Unset `BILLING_SECRET`, verify fallback to api_secret_key still works.
- Snippets: search with `test,id.eq.something` -- should be sanitized to `testideqsomething` (harmless). Search with `%%%` -- should be stripped to empty and skipped (returns all snippets, no filter).
- Client portal: verify `/api/v1/portal/{tenant_id}/public/{token}` returns `api_base` matching the `API_URL` env var, not the hardcoded Railway URL.

## Concerns
- The second hardcoded URL at line 751 (in the authenticated client portal endpoint) was also replaced -- same bug, same fix. This was not explicitly called out in the task but is clearly the same issue.
- No `from __future__ import annotations` was used in any file.
