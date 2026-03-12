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

_New entries are auto-appended by the bug logging GitHub Action. Add root cause details with /log-bug._
