# Nightly Commit Review — 2026-08-02

**Run time:** 2026-08-02 (automated)
**Commits reviewed:** 5 (last 24h)
**Issues found:** 1 LOW (fixed inline), 0 MEDIUM/HIGH

---

## Commit Triage

### LOW — `49e4255` ops: nightly-commit-review 2026-08-01
- Nightly ops log from yesterday's run
- No code changes

### LOW — `9f711ea` ui: defer M365 + HubSpot cards off Integrations page (#621)
- One-file UI change (`frontend/src/pages/IntegrationsPage.jsx`)
- Deferred 2 integration cards from the page; purely presentational
- No logic changes, no schema touches

### MEDIUM — `2869124` fix: AI Workforce gate must honor grandfathered plans (#620)
- Plan-gating fix in `backend/routers/os_orchestrate.py`
- Changed exact-match `"agent_os"` check to `not in AGENT_OS_PLANS` set
- Correctly now honors `growth/autopilot/professional/enterprise` grandfathered plans per CLAUDE.md
- Test coverage: 43 tests passing per commit message
- **No bugs found** — correct fix, consistent with `agent_os_gate.AGENT_OS_PLANS` used elsewhere

### MEDIUM — `c5a5a62` feat: PWA installability + escalation push (#622)
- PWA manifest icons (192/512px) + generic `send_owner_push` function
- `send_pending_approval_push` refactored to delegate to `send_owner_push`
- `push_subscriptions` table legitimately uses `tenant_id` (OS-adjacent table, not leads/conversations)
- Escalations service correctly passes `client_id` as `tenant_id=client_id` to push service
- **No bugs found**

### MEDIUM — `b67710c` feat: capabilities phases 1–5 — inbox monitoring, SMS agent, social publish+images, prospecting, in-chat connectors (#619)
- 62 files, 13,916 insertions — largest commit in recent history
- All new services reviewed for critical invariants:
  - `client_id` used correctly on `escalations`, `prospects`, `conversations`, `leads` tables ✓
  - `tenant_id` used correctly on `social_posts`, `push_subscriptions`, `widget_configs` ✓
  - No `from __future__ import annotations` in any FastAPI file ✓
  - `status` (not `lead_stage`) used on leads ✓
- Gmail OAuth flow mirrors existing Google Calendar pattern (signed-JWT state token, 10-min expiry) ✓
- RLS enabled on new tables (migrations 190/191/193 confirm per-table policies) ✓
- **One LOW bug found and fixed** (see Fixes section below)

---

## Fixes Applied

### `backend/routers/connectors.py` — stale module docstring
- **Bug:** Docstring said "Intentionally NOT registered in `backend/main.py` yet" but
  `connectors_router.router` is registered at `main.py:1067`
- **Risk:** LOW — misleading documentation only; zero runtime impact
- **Fix:** Updated docstring to reflect actual registration state
- **Commit SHA:** this run
- **Tests:** venv unavailable in execution environment; docstring change has no runtime
  effect; CI will confirm

---

## Summary

All commits reviewed. No auth/payments/tenant-isolation issues found. No MEDIUM/HIGH bugs. One stale documentation comment (LOW) fixed inline. The large capabilities commit (b67710c) introduces substantial new surface area but follows project invariants correctly throughout.
