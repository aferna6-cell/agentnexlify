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

_New entries are auto-appended by the bug logging GitHub Action. Add root cause details with /log-bug._
