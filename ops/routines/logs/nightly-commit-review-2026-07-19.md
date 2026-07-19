# Nightly Commit Review — 2026-07-19

**Run time:** 2026-07-19 (automated)
**Window:** last 24 hours
**Commits reviewed:** 4
**Bugs fixed:** 0
**Issues created:** 0
**Verdict:** CLEAN — no bugs, no invariant violations, all CLAUDE.md critical rules honored.

---

## Commits

### 1. `6aa9ba4` — Repo cleanup: delete 970 verified-stale files (#477)
**Risk:** LOW
**Files:** `.gitignore`, `STRUCTURE.md`, `scripts/check_project_invariants.py` (removed dead path refs), `specs/lead-parser-replacement_spec.md` (migrated from old location)
**Triage:** Pure cleanup — HTML scrapes, docs dumps, old audit files, stale subconscious runs, shipped plans. All 970 deletions verified zero inbound refs before removal. Modified files are minimal: `check_project_invariants.py` had dead skip-paths removed, `.gitignore` had dead entries removed, `STRUCTURE.md` updated to reflect spec canonical location.
**Action:** None.

---

### 2. `6b0b0bc` — feat(ops): platform_settings DB flags + admin voice test call (migration 175) (#476)
**Risk:** MEDIUM
**Files:** `backend/services/platform_flags.py` (new), `backend/routers/admin_voice_test.py` (new), `backend/services/llm_runtime.py`, `backend/services/referral_reward.py`, `backend/tests/test_platform_flags.py` (new), `backend/tests/test_admin_voice_test.py` (new), `migrations/175_platform_settings.sql`, `docs/dev-knowledge/schema-log.md`

**Triage:**

`platform_flags.py`: fail-open pattern (DB errors return None → caller uses env fallback). 60s process-level cache. TESTING no-op. Clean.

`admin_voice_test.py`: POST /api/v1/admin/voice-test-call. Admin-secret gated (same guard as loop-health). Rate-limited (10/min). E.164 validated. TwiML XML-escaped with `re.sub(r"[<>&]", " ", req.say)`. From/to differ enforced. httpx timeout=15. Error returns 502, not 500. Clean.

`llm_runtime.py resolve_int_setting`: DB override now bypasses `minimum` parameter (returns parsed value if `>= 0`). **Intentional kill-switch semantics** — setting DB row to "0" disables a feature even if env has "1". Documented in code comment and test `test_resolve_int_setting_db_override_wins_and_zero_kills`. Minor concern: if a DB row is accidentally set to 0 for something like `voice_chat_max_tokens`, the Twilio/Claude call would receive `max_tokens=0` and fail. Mitigation: only flag names that are feature toggles (not size limits) should be set in `platform_settings`. No current production rows at risk — prod seeded values are all "1" (enable flags). Log observation for awareness, not a blocker.

CLAUDE.md invariants:
- No `from __future__ import annotations` ✓
- `platform_settings` table is a new table, not modifying `leads`/`conversations` ✓
- Migration 175 applied per commit message ✓
- Tests added ✓

**Action:** None. Minor note on `resolve_int_setting` minimum bypass added above for awareness.

---

### 3. `23b1da5` — Close out issues #454, #465, #453: appointment auto-complete, loop-health dashboard, attribution page (#475)
**Risk:** MEDIUM
**Files:** `backend/services/automation/scheduled/appointment_jobs.py`, `backend/routers/analytics/insights.py`, `backend/services/automation/scheduled_jobs.py`, `backend/services/automation_engine.py`, `frontend/src/pages/AttributionPage.jsx`, `frontend/src/pages/BotHealthPage.jsx`, `frontend/src/components/Sidebar.jsx`, `frontend/src/components/App.jsx`, `frontend/src/utils/api/analytics.js`, plus tests and PR-check CI updates.

**Triage:**

`auto_complete_past_appointments()`: Cross-tenant service-role query (correct for a scheduled job). Filters `confirmed`/`booked` rows past `end_time + 1h grace`. Internal tenant guard fails closed (returns 0 if tenant lookup fails). Idempotent via status filter — completed rows never re-processed. `check_appointment_triggers(appt_id, completed=True)` matches function signature at `rule_engine.py:743`. Each appointment update guarded with `.in_("status", ["confirmed", "booked"])` as a second idempotency layer. Minor note: processes `BATCH_LIMIT` rows per run (5-min cadence) — historical debt from before this deploy will drain across multiple cycles, not in one shot. Expected behavior; not a bug.

`attribution_breakdown()`: Uses `client_id` correctly on `leads` table (CLAUDE.md critical invariant #1 honored). `verify_tenant(claims, tenant_id)` called. 5000-lead hard limit — adequate for most tenants; large tenants (>5k leads) will see truncated attribution totals. Not a bug but a known ceiling. Pre-existing pattern from `lead_source_breakdown` which also uses `.eq("client_id", tenant_id)`.

Frontend `BotHealthPage`/`AttributionPage`: No `localStorage` usage (CLAUDE.md critical rule #6 honored). Admin-secret prompt pattern matches existing `AdminFunnelPage`. No security concerns.

CLAUDE.md invariants:
- No `from __future__ import annotations` ✓
- `leads` table uses `client_id` not `tenant_id` ✓
- `appointments` table uses `tenant_id` ✓
- No schema migrations (uses existing migration 172 attribution column) ✓
- Tests added for all three features ✓

**Action:** None.

---

### 4. `c8d33bd` — ops: nightly-commit-review 2026-07-18
**Risk:** LOW
**Files:** `ops/routines/logs/nightly-commit-review-2026-07-18.md`
**Triage:** Previous night's automated log commit. No code changes.
**Action:** None.

---

## Summary

All 4 commits this window are clean. No bugs requiring immediate fixes. No HIGH-risk changes (no auth, payments, or tenant isolation modifications). Both MEDIUM commits (#476, #475) are well-tested and respect all CLAUDE.md critical invariants.

Two minor observations logged (no action required):
1. `resolve_int_setting` DB override bypasses `minimum` parameter — intentional kill-switch semantics, tested, but `platform_settings` rows should only be set for feature toggle keys, not for size/count settings.
2. Attribution endpoint hard-caps at 5000 leads — large tenants will see incomplete totals. Same ceiling pattern as existing `lead_source_breakdown`.
