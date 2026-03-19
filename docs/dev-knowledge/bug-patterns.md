# Bug Patterns — AgentNexLiFy

Bugs that have been found and fixed. Claude Code reads this to avoid re-discovering known problems. Auto-updated by the bug logging GitHub Action on fix commits.

---

### from __future__ import annotations breaks FastAPI routes
**Date:** 2025
**Symptom:** Every POST/PUT request returns 422 regardless of payload.
**Root Cause:** `from __future__ import annotations` makes type hints strings. FastAPI/Pydantic can't parse Body models at runtime.
**Files Changed:** Router files that had the import
**Fix:** Remove the import from all router files.
**Prevention:** Pre-commit hook blocks this. Never add to router files.

---

### CORS errors blocking widget on external sites
**Date:** 2025
**Symptom:** Chat widget loads but API calls fail with CORS errors.
**Root Cause:** Customer domain not in FastAPI CORS allowlist.
**Files Changed:** backend/main.py
**Fix:** Added domain to CORS origins list.
**Prevention:** Add customer domains to CORS during onboarding.

---

### Lead capture silently failing — tenant_id vs client_id
**Date:** 2025
**Symptom:** Conversations work but no leads appear in dashboard.
**Root Cause:** Code used tenant_id for leads table, but the actual column is client_id. Error swallowed by bare except.
**Fix:** Changed to client_id. Added error logging.
**Prevention:** Pre-commit hook warns on bare excepts. Schema-guard skill documents this.

---

### Lead pipeline crash — lead_stage vs status
**Date:** 2025
**Symptom:** Leads page crashes or shows empty pipeline.
**Root Cause:** Code used lead_stage, but the actual column is status.
**Fix:** Updated all references to status.
**Prevention:** Schema-guard skill. CLAUDE.md documents correct column names.

---

### Dashboard shows FREE when user has paid plan
**Date:** 2025
**Symptom:** User pays but dashboard still shows FREE.
**Root Cause:** Plan read from JWT claims which don't refresh on upgrade.
**Fix:** Fetch plan from live API endpoint.
**Prevention:** Never use JWT for display data that can change.

---

### Stripe webhook fires but database not updated
**Date:** 2025
**Symptom:** Payment succeeds in Stripe but plan not updated in database.
**Root Cause:** No error logging in webhook handler. Missing plan mapping (foundation→growth, operations→professional).
**Fix:** Added logging, fixed mapping, fixed update query.
**Prevention:** All webhook handlers must have error logging. Migration 013 fixed plan names.

---

### Conversation memory not working
**Date:** 2025
**Symptom:** AI ignores previous messages in widget chat.
**Root Cause:** Session ID regenerating each request instead of persisting.
**Fix:** Fixed session ID persistence in widget.
**Prevention:** Test multi-turn conversations after widget changes.

---

### Vercel build failure — missing component
**Date:** 2025
**Symptom:** Deploy fails with "Module not found".
**Root Cause:** Imported component file didn't exist.
**Fix:** Created missing component or removed import.
**Prevention:** Pre-push hook runs `npm run build`. PR check validates builds.

---

### Billing UI plan name fallbacks
**Date:** 2025-03
**Symptom:** Plan name displays incorrectly after plan rename migration.
**Root Cause:** Frontend had hardcoded old plan names (foundation, operations).
**Fix:** Added fallback mappings and unlimited conversation display.
**Prevention:** Use canonical plan names from CLAUDE.md (free, growth, professional, enterprise).

---

### Business page settings 500 error
**Date:** 2025-03
**Symptom:** Settings page returns 500 Internal Server Error.
**Root Cause:** NULL database values causing Pydantic model construction to fail.
**Fix:** Handle NULL values in Pydantic model construction.
**Prevention:** Always handle nullable DB columns in Pydantic models.

---

### Conversation counter never increments — undefined variable `used`
**Date:** 2026-03
**Symptom:** `conversations_used_this_month` stays at 0 for all tenants.
**Root Cause:** `widget.py:551` referenced variable `used` which was never defined. NameError caught by `except Exception` block silently.
**Fix:** Changed to `tenant.get("conversations_used_this_month", 0)`.
**Prevention:** Avoid variable references without assignment. Silent except blocks hide these bugs.

---

### Sequence stats endpoint queries nonexistent column
**Date:** 2026-03
**Symptom:** "Emails sent today" metric always shows 0 or errors silently.
**Root Cause:** `sequences.py:250` queried `automation_logs.tenant_id` but automation_logs has no `tenant_id` column.
**Fix:** Query through `automation_executions` (which does have `tenant_id`) then filter logs by execution IDs.
**Prevention:** Always verify column existence before writing queries (use schema-guard skill).

---

### Widget model ID mismatch
**Date:** 2026-03
**Symptom:** All AI chat responses return generic fallback instead of real AI.
**Root Cause:** `widget.py` MODEL constant set to `claude-sonnet-4-5-20250929` which may not be accessible. CLAUDE.md specifies `claude-sonnet-4-5-20250514`.
**Fix:** Updated MODEL to `claude-sonnet-4-5-20250514`.
**Prevention:** Keep model constants in sync with CLAUDE.md documentation.

---

### Widget config missing agent_name — generic "Agent" in header
**Date:** 2026-03
**Symptom:** Widget header shows "Agent" instead of the business name.
**Root Cause:** `WidgetConfigResponse` model didn't include `agent_name` field, and the config endpoint didn't return it.
**Fix:** Added `agent_name` field to model, populated from `tenant.business_name` in endpoint.
**Prevention:** When widget JS expects a field from the config endpoint, ensure it's in the response model.

---

### Widget test page missing data-api-base
**Date:** 2026-03
**Symptom:** Widget test page loads but API calls 404.
**Root Cause:** `widget-test.html` had `data-api-key` but no `data-api-base`. Widget inferred backend URL from script src (Vercel), not Railway.
**Fix:** Added `data-api-base="https://agentnexlify-production.up.railway.app"`.
**Prevention:** Always include `data-api-base` in widget embed code pointing to Railway backend.

---

### Appointment automation template never triggers
**Date:** 2026-03-11
**Symptom:** "Appointment Booked Series" automation sequence never fires when a lead's status changes to `appointment_booked`.
**Root Cause:** Template in `sequences.py` used `{"target_stage": "appointment"}` but the valid stage value is `"appointment_booked"`. The automation engine compares `target_stage` against the new stage and they never match.
**Fix:** Changed `target_stage` from `"appointment"` to `"appointment_booked"` in `backend/routers/sequences.py:81`.
**Files:** `backend/routers/sequences.py`
**Prevention:** Always validate trigger_config values against `VALID_LEAD_STAGES` in `backend/models/schemas.py`. Consider adding validation in the template creation code.

---

### BaseException catches preventing graceful shutdown
**Date:** 2026-03-11
**Symptom:** Worker processes don't shut down cleanly; `except BaseException:` catches `KeyboardInterrupt`, `SystemExit`, and `asyncio.CancelledError`.
**Root Cause:** 10 `except BaseException:` blocks in `widget.py` were catching ALL exceptions including signals meant for process control. One was `except BaseException: pass` — completely silent.
**Fix:** Changed all to `except Exception:`. Added logging to the previously silent `score_lead_background` catch.
**Files:** `backend/routers/widget.py`
**Prevention:** Never use `except BaseException:` unless explicitly handling shutdown signals. The pre-commit hook should flag this pattern.

---

### Silent analytics fallbacks hiding database errors
**Date:** 2026-03-11
**Symptom:** Dashboard analytics show 0 for conversations, leads, appointments, or emails with no error indication.
**Root Cause:** 6 `except Exception:` blocks in `analytics.py` silently defaulted values to 0 without any logging. Database connection failures or schema mismatches would make the dashboard show zeros.
**Fix:** Added `logger.warning(...)` to all 6 fallback blocks in `analytics.py`.
**Files:** `backend/routers/analytics.py`
**Prevention:** Every except block that returns a default value must log a warning. Silent fallbacks mask real problems.

---

### AI email automation using wrong model ID
**Date:** 2026-03-11
**Symptom:** AI-generated follow-up emails may fail or use an unavailable model.
**Root Cause:** `automation_engine.py:440` had `model="claude-sonnet-4-5-20250929"` — same wrong model ID as the earlier widget fix. The correct model is `claude-sonnet-4-5-20250514`.
**Fix:** Updated model ID to `claude-sonnet-4-5-20250514`.
**Files:** `backend/services/automation_engine.py`
**Prevention:** Keep model IDs centralized (widget.py MODEL constant) and check all usages when updating.

---

### Invalid plan fallback in AuthContext
**Date:** 2026-03-11
**Symptom:** Users without a plan in JWT claims get assigned plan `"starter"` which is not a valid plan name (valid: free, growth, professional, enterprise).
**Root Cause:** `AuthContext.jsx:36` had `plan: payload.plan || "starter"` — `"starter"` was never a valid plan name.
**Fix:** Changed fallback to `"free"`.
**Files:** `frontend/src/context/AuthContext.jsx`
**Prevention:** Only use canonical plan names from CLAUDE.md.

---

### International phone numbers not captured by widget
**Date:** 2026-03-12
**Symptom:** Widget chat captures US phone numbers (555-123-4567) but silently drops international formats (+44 20 1234 5678, +91 98765 43210).
**Root Cause:** `PHONE_RE` in `widget.py:91` only matched US 10-digit pattern with optional `+1`. Country codes beyond +1 and non-3-3-4 digit groupings were ignored.
**Fix:** Updated regex to support country codes +1 through +999, variable digit groupings (2-4 digits per group), and added E.164 validation (7-15 total digits) to prevent false positives.
**Files:** `backend/routers/widget.py`
**Prevention:** Test phone extraction with international formats when modifying the regex. Minimum 7 digits prevents matching random numbers.

---

### Appointment times displayed in wrong timezone
**Date:** 2026-03-12
**Symptom:** Calendar and dashboard show appointment times in the browser's local timezone instead of the business's configured timezone. A 2 PM PST appointment shows as 5 PM for an EST user.
**Root Cause:** `Calendar.jsx` had a `formatTime(isoStr, tz)` function that accepted a timezone parameter, but it was never passed — all calls were `formatTime(a.start_time)` without the tz argument. `TodayAppointments.jsx` didn't support tz at all. The API didn't return the business timezone with appointments.
**Fix:** Added `timezone` field to `AppointmentListResponse` (populated from `business_hours` table). Both Calendar.jsx and TodayAppointments.jsx now extract and pass the timezone to all `formatTime()` calls.
**Files:** `backend/models/schemas.py`, `backend/routers/appointments.py`, `frontend/src/pages/Calendar.jsx`, `frontend/src/pages/Dashboard/TodayAppointments.jsx`
**Prevention:** When displaying user-facing times, always use the business timezone from the API, never browser-local time.

---

### Twilio webhook signature not validated — spoofing risk
**Date:** 2026-03-12
**Symptom:** Any HTTP client could POST to the Twilio webhook endpoint and trigger SMS-related logic without authentication.
**Root Cause:** The SMS/Twilio endpoint accepted all incoming requests without verifying the `X-Twilio-Signature` HMAC-SHA1 header.
**Fix:** Added Twilio signature validation using HMAC-SHA1 verification against the configured auth token.
**Files:** Backend Twilio/SMS endpoints
**Prevention:** All inbound webhook endpoints must validate signatures from the sending service.

---

### SMS rate limit used stale JWT plan instead of live DB
**Date:** 2026-03-11
**Symptom:** Users who upgraded their plan still hit the old plan's SMS rate limit until they re-logged in.
**Root Cause:** SMS endpoint read the plan from JWT claims (which don't refresh on upgrade) instead of querying the database for the current plan.
**Fix:** Changed SMS endpoint to fetch plan from the tenants table directly.
**Files:** Backend SMS endpoint
**Prevention:** Never use JWT claims for data that can change (plans, limits). Always fetch live from DB. Same pattern as the dashboard plan display bug.

---

### Sequence builder offered invalid target stages
**Date:** 2026-03-11
**Symptom:** Automation sequences created via the SequenceBuilder UI could set target stages like "qualified" or "appointment" that don't exist in the system, causing sequences to never trigger.
**Root Cause:** SequenceBuilder stage dropdown had hardcoded values that didn't match the actual valid stages (new, contacted, appointment_booked, closed, lost).
**Fix:** Updated stage options to match `VALID_LEAD_STAGES` from the schema.
**Files:** Frontend SequenceBuilder component
**Prevention:** Stage options should be derived from the backend's `VALID_LEAD_STAGES` constant, not hardcoded in the frontend.

---

### Google Calendar API calls duplicated in IntegrationsPage
**Date:** 2026-03-11
**Symptom:** IntegrationsPage had inline fetch calls to Google Calendar endpoints with hardcoded BASE URLs and duplicated error handling, creating maintenance burden and inconsistency.
**Root Cause:** Google Calendar integration was added before the centralized `api.js` utility existed, so the page made raw fetch calls.
**Fix:** Replaced inline fetch calls with centralized `api.js` functions.
**Files:** `frontend/src/pages/IntegrationsPage.jsx`, `frontend/src/utils/api.js`
**Prevention:** All API calls should go through `api.js` — never inline fetch with hardcoded URLs.

---

### Dashboard crash — migrations not applied to live database
**Date:** 2026-03-12
**Symptom:** Dashboard crashes on load. Error: "column widget_configs.is_online does not exist"
**Root Cause:** Migrations 014-023 existed as SQL files in the repo but were never run against the live Supabase database. The code referenced columns that didn't exist yet.
**Files Changed:** Applied migrations 014-024 to live Supabase
**Fix:** Ran all missing migrations in order. Created migration 024 for appointments.updated_at.
**Prevention:** After creating any migration file, it MUST be run on live Supabase immediately. The continuous loop must NEVER create migrations without flagging them for manual execution. Add a check: if new migration files exist that aren't in schema-log.md as "applied", flag it as a P0 task.

---

### Chat widget returning "having trouble" — invalid Claude model ID
**Date:** 2026-03-12
**Symptom:** Widget loads but AI responds with "I'm sorry, I'm having trouble right now." No useful error shown to developer.
**Root Cause:** Model ID was set to "claude-sonnet-4-5-20250514" which returns 404 from the Anthropic API — that model doesn't exist. The continuous loop likely updated the model ID incorrectly during an optimization cycle.
**Files Changed:** widget.py, automation_engine.py, reviews.py, demo app — all 4 files that reference the Claude model
**Fix:** Changed model ID to "claude-sonnet-4-6" in all files.
**Prevention:** NEVER change Claude model IDs without verifying the model exists. Valid model IDs as of March 2026: claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5-20251001. The continuous loop must add model ID changes to the business logic gate — verify the API accepts the model before committing.

---

### Widget online-status toggle was unauthenticated
**Date:** 2026-03-12
**Symptom:** The dashboard's widget online/offline toggle could be changed without dashboard auth, and oversized widget messages had no schema-level cap.
**Root Cause:** `PUT /api/v1/widget/config/{tenant_id}/online-status` accepted writes without verifying JWT claims against the tenant, and `WidgetChatRequest.message` had no `max_length` validation.
**Files Changed:** `backend/routers/widget.py`, `backend/models/schemas.py`
**Fix:** Added JWT-based tenant verification to the toggle endpoint and capped widget message bodies at 10,000 characters in the request model.
**Prevention:** All dashboard-only widget config endpoints must use the same JWT/tenant dependency pattern as other authenticated routes. Public widget payload models need explicit upper bounds for message/content fields.

---

### Scheduled headless routines failed in non-interactive shells
**Date:** 2026-03-12
**Symptom:** Morning/evening scheduled runs either stalled waiting for permissions or failed immediately with `claude: command not found`, leaving only partial log output.
**Root Cause:** Headless automation depended on interactive PATH resolution for `claude`, used UTC-dated log filenames that drifted past local evening runs, and let `git pull --rebase` emit avoidable errors on dirty worktrees before the actual headless step started.
**Files Changed:** `scripts/daily/morning-auto.sh`, `scripts/daily/evening-auto.sh`, `scripts/daily/setup-cron.sh`, `scripts/daily/setup-scheduler.ps1`, `scripts/continuous-loop.sh`, `docs/scheduled-routines.md`
**Fix:** Switched the routines to shared runtime preflight/logging helpers, local-date log naming, clean-worktree pull skipping, a static pre-run health snapshot, and persisted Claude CLI resolution for cron/Task Scheduler.
**Prevention:** Any scheduled headless entrypoint must validate its CLI dependency at runtime, not just at install time. Scheduler wrappers should persist the CLI location or PATH, and daily logs should use the same local date basis as the human routine.

---

### Anthropic client default timeout blocks workers for 30 minutes
**Date:** 2026-03-15
**Symptom:** Widget chat hangs indefinitely when Claude API is slow/degraded. Workers become unresponsive.
**Root Cause:** The Anthropic Python SDK defaults to 600s read timeout with 2 retries (3 attempts). A single slow request could block a worker thread for up to 30 minutes. With 4 workers, 4 concurrent slow requests = entire backend unresponsive.
**Fix:** Added `timeout=30.0` to all 10 `anthropic.Anthropic()` calls across 8 files.
**Files Changed:** widget.py, content.py, reviews.py, jobs.py, snippets.py, menu.py, automation_engine.py
**Prevention:** Always set explicit timeout when creating Anthropic clients. Never rely on SDK defaults for production code.

---

### Health check always returns "ok" even when database is down
**Date:** 2026-03-15
**Symptom:** Monitoring shows "ok" but entire application returns 500 errors on every request.
**Root Cause:** `/health` endpoint checked Supabase connectivity but always returned `status: "ok"` regardless of the result.
**Fix:** Returns `status: "degraded"` when Supabase is unreachable.
**Files Changed:** backend/main.py
**Prevention:** Health check status must reflect actual service health. If any critical dependency is down, status should not be "ok".

---

### leads.service_interest column doesn't exist — areas_of_interest is correct
**Date:** 2026-03-15
**Symptom:** Lead service interest never saved; Supabase errors silently swallowed.
**Root Cause:** Code referenced `service_interest` column but live DB has `areas_of_interest` (schema drift from early development). The code worked because errors were caught and silently ignored.
**Fix:** Updated all references in widget.py to use `areas_of_interest`. Fixed lead dedup query to include `areas_of_interest` and `conversation_summary`.
**Files Changed:** backend/routers/widget.py
**Prevention:** Always verify column names against live schema before writing queries. CLAUDE.md now documents the correct column name.

---

### check_no_response_leads dedup never matched — re-enrolled every 60 seconds
**Date:** 2026-03-18
**Symptom:** Leads with no chat response got enrolled in the no_response_24h sequence on every automation loop tick (every 60 seconds), spamming them with emails.
**Root Cause:** The dedup check in `check_no_response_leads` queried `automation_executions` with `.eq("status", "active")`, but `trigger_sequence` inserts executions with `"status": "in_progress"`. These never match, so the dedup check always returned no rows and every lead was re-enrolled every 60 seconds.
**Fix:** Changed the dedup query to `.in_("status", ["active", "in_progress"])` so both statuses are recognized. Also refactored to a batch query (Q2a/Q2b) — collect all lead IDs, fetch all their executions in one query, then fetch sequence trigger_events in a second query. Builds `already_enrolled_lead_ids` set entirely in Python.
**Files Changed:** `backend/services/automation_engine.py`
**Prevention:** When inserting a row with a specific status, ensure any dedup/existence checks query for that exact status value. The insert status and the dedup filter must match.

---

### check_no_response_leads N+1 queries — 3-5 DB queries per lead
**Date:** 2026-03-18
**Symptom:** With 50 leads, the function issued up to 250 DB round-trips per loop iteration, adding measurable latency to the 60-second automation loop.
**Root Cause:** Three inner queries (enrollment dedup, conversations session_id, chat_messages latest timestamp) ran inside a per-lead for-loop. With BATCH_LIMIT=50 leads that's 150-250 queries for what should be a single pass.
**Fix:** Refactored `check_no_response_leads` to batch all reads before the loop:
  - Q1: fetch candidate leads (unchanged)
  - Q2a: single `.in_("lead_id", all_lead_ids)` + `.in_("status", ["active","in_progress"])` on automation_executions
  - Q2b: single `.in_("id", enrolled_seq_ids)` on automation_sequences to get trigger_events
  - Q3: single `.in_("id", all_conv_ids)` on conversations for session_id mapping
  - Q4: single `.in_("session_id", all_session_ids)` on chat_messages ordered desc; Python dedup by first occurrence per session_id
  - Lead evaluation loop is now pure Python with zero additional DB calls
Also refactored `trigger_sequence` to batch-fetch first steps: single `.in_("sequence_id", seq_ids)` query instead of one query per sequence; groups by sequence_id in Python.
**Files Changed:** `backend/services/automation_engine.py`
**Prevention:** Any for-loop over a batch of DB rows that queries inside the loop is an N+1 pattern. Collect all IDs first, batch-fetch with `.in_()`, then join in Python.

---

### Campaign send endpoint blocks request thread until all emails sent
**Date:** 2026-03-18
**Symptom:** POST /campaigns/send hangs for minutes when sending to large lead lists, eventually timing out. Other API requests back up behind it.
**Root Cause:** The campaign send loop (iterating leads, sending emails/SMS) ran synchronously inside the request handler. A 500-lead campaign blocked the worker for the entire send duration.
**Files Changed:** `backend/routers/marketing_campaigns.py`, `migrations/055_campaign_sending_started_at.sql`
**Fix:** Extracted send loop into `_send_campaign_background()`, dispatched via `asyncio.create_task()`. Endpoint returns immediately. Background task marks campaign failed on error. Migration 055 adds `sending_started_at` for stall detection (>30 min).
**Prevention:** Any operation that iterates and sends (emails, SMS, webhooks) must run as a background task, never in the request handler. Check for `asyncio.create_task()` pattern.

*Auto-logged — needs human enrichment for root cause details*

---

### GBP OAuth redirect URI pointed to frontend instead of backend
**Date:** 2026-03-18
**Symptom:** Google Business Profile OAuth callback fails with redirect_uri_mismatch error.
**Root Cause:** `gbp.py` used `frontend_url` for the OAuth redirect URI, but the callback endpoint is on the backend (Railway).
**Files Changed:** `backend/routers/gbp.py`, `backend/config.py`
**Fix:** Changed redirect URI to use `api_url` (Railway production URL). Added `api_url` setting to config.py.
**Prevention:** OAuth redirect URIs must point to the backend API server, not the frontend.

*Auto-logged — needs human enrichment for root cause details*

---

### conversations.lead_id FK missing ON DELETE clause — dangling references
**Date:** 2026-03-18
**Symptom:** Deleting or merging a lead leaves orphaned `lead_id` references in the conversations table. No error raised, but conversations reference non-existent leads.
**Root Cause:** The original FK constraint on `conversations.lead_id` had no `ON DELETE` clause, defaulting to `RESTRICT` or `NO ACTION`. Lead delete/merge operations didn't cascade.
**Files Changed:** `migrations/058_fix_conversations_lead_fk.sql`
**Fix:** Migration 058 drops and re-creates the FK with `ON DELETE SET NULL`.
**Prevention:** All FK constraints referencing leads should use `ON DELETE SET NULL` or `ON DELETE CASCADE` depending on the relationship. Check existing FKs when adding new tables that reference leads.

*Auto-logged — needs human enrichment for root cause details*

---

### Frontend-backend field name mismatches — silent data display failures
**Date:** 2026-03-20
**Symptom:** Data exists in DB but never displays in the UI. No errors in console. Fields show "?" or "—" or empty.
**Root Cause:** Frontend reads a different property name than what the backend returns from Supabase `SELECT *`. Common pattern: backend stores `items_json`, `data_json`, `cached_lead_count`, `stripe_payment_link` but frontend reads `items`, `data`, `lead_count`, `payment_link`.
**Fix:** Align frontend property names to match the actual DB column names returned by Supabase. Affected files: SmartListsPage.jsx, FormBuilderPage.jsx, InvoicesPage.jsx.
**Prevention:** When creating a new page that reads from a Supabase table, verify the column names in the migration SQL file. The backend uses `SELECT *` which returns raw column names — do not assume camelCase or shortened names.

---

### Frontend-backend filter key mismatches — filters silently ignored
**Date:** 2026-03-20
**Symptom:** Smart Lists filters appear to work (no errors) but return all leads regardless of filter values.
**Root Cause:** Frontend `emptyFilters` used keys `statuses`, `temperature`, `tags` but backend `_apply_filters()` expected `status`, `lead_temperature`, `tags_include`. Since `filter_json` is saved as JSONB and re-read by the backend, mismatched keys are silently skipped.
**Fix:** Updated frontend filter keys to match backend expectations.
**Prevention:** When building filter UIs, check the backend filter-parsing function for the exact key names it reads with `.get()`.

---

### Frontend request body mismatch — 422 errors on actions
**Date:** 2026-03-20
**Symptom:** Pipeline drag-drop and invoice mark-paid fail with 422 Unprocessable Entity.
**Root Cause:** (1) PipelinePage sent `{ new_stage: ... }` but backend Pydantic model expected `{ status: ... }`. (2) markInvoicePaid sent no body but backend expected a Pydantic model body (even with all-optional fields, FastAPI requires valid JSON).
**Fix:** Corrected field name to `status` and added `body: {}` to markInvoicePaid.
**Prevention:** Always check the backend Pydantic request model field names before writing the frontend API call. For POST/PUT endpoints with Pydantic Body params, always send at least `{}`.

---

### Frontend reads nested property for top-level column
**Date:** 2026-03-20
**Symptom:** Form active/inactive status badge always shows "Active" regardless of actual state.
**Root Cause:** FormBuilderPage read `form.settings_json?.is_active` but `is_active` is a top-level column on the `forms` table, not nested inside `settings_json`. Since `undefined !== false` evaluates to `true`, all forms appeared active.
**Fix:** Changed to `form.is_active !== false`.
**Prevention:** Check the migration SQL to distinguish between top-level columns and JSONB-nested fields before accessing properties.

---

### conversations table uses client_id — not tenant_id (regression of lead capture bug)
**Date:** 2026-03-20
**Symptom:** Inbox assign, reply, notes, and conversation tag updates all return 404 "Conversation not found" despite conversations existing in the database.
**Root Cause:** `conversation_inbox.py` and `auth.py` queried the `conversations` table with `.eq("tenant_id", tenant_id)`, but the conversations table FK column is `client_id` (same as the leads table). This is a regression of the original `client_id` vs `tenant_id` bug pattern.
**Fix:** Changed all conversations-table queries in `conversation_inbox.py` (4 locations) and `auth.py` `update_conversation_tags` (2 locations) from `tenant_id` to `client_id`.
**Prevention:** Both `leads` and `conversations` tables use `client_id` as their FK to tenants — NEVER use `tenant_id` when querying either table. This is now documented in CLAUDE.md.

---

### Frontend passes session_id but backend expects UUID — inbox operations broken
**Date:** 2026-03-20
**Symptom:** All inbox operations (assign, notes, reply) return 404 even after fixing client_id. Conversations exist but can't be found.
**Root Cause:** ConversationsPage.jsx stores `conv.session_id` as the selected identifier and passes it to all inbox API calls. But the backend `conversation_inbox.py` looked up conversations by `.eq("id", conversation_id)` — the UUID primary key. Since session_id and UUID id are different values, no matches were found.
**Fix:** Added `_find_conversation()` helper that tries UUID lookup first, then falls back to session_id + client_id lookup.
**Prevention:** When building endpoints that receive IDs from the frontend, verify what the frontend actually sends (check the React component's state and API call). Don't assume UUID — the frontend may use a natural key like session_id.

---

_New entries are auto-appended by the bug logging GitHub Action. Add root cause details with /log-bug._
