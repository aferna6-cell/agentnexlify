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

_New entries are auto-appended by the bug logging GitHub Action. Add root cause details with /log-bug._
