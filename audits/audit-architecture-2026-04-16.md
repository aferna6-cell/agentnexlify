# Architecture Health Report — 2026-04-16

## CRITICAL (fix before next deploy)

- [ ] **N+1 Query in `process_pending_steps()`** | Pass 6 | Effort: M
  - `backend/services/automation_engine.py:147-154` — loops over 50 execution rows, calls `execute_step()` per row which re-fetches each execution individually (line 162-168). 50+ DB calls per batch instead of 1.
  - Fix: Batch-load all execution data in `process_pending_steps()`, pass to `execute_step()`.

- [ ] **Anthropic SDK Version Mismatch** | Pass 5 | Effort: S
  - `backend/requirements.txt:4` pins `anthropic==0.42.0`; runtime is `0.95.0`. Silent compatibility drift.
  - Fix: Update to `anthropic>=0.95.0,<1`.

- [x] **Services Importing Router Functions** | Pass 2 | Effort: M — FIXED 2026-04-16
  - Created `backend/services/auth_service.py` — `_jwt_secret`, `_decode_token`, `get_current_tenant`
  - Created `backend/services/campaign_service.py` — `_send_campaign_background`
  - Moved `_generate_reschedule_token` + `build_reschedule_url` into `backend/services/booking.py`
  - All 4 call sites updated; `_get_current_tenant` in `auth.py` kept as alias for backward compat
  - Residual: `backend/services/industry_packs/seed.py:127` imports `_FORM_PRESETS` from forms router (not in original 4)

---

## HIGH (fix this sprint)

- [ ] **God Class: `automation_engine.py` (4,285 lines)** | Pass 1 | Effort: L
  - Handles: sequence triggering/execution, email/SMS delivery, appointment/review/billing workflows, rule evaluation.
  - Fix: Split into `sequence_executor.py`, `email_campaign_dispatcher.py`, `workflow_scheduler.py`, `rule_evaluator.py`. Coordination in `automation_orchestrator.py`.

- [ ] **Widget JS duplicated × 3** | Pass 1 | Effort: M
  - Identical copies at:
    - `widget/agentnexlify-widget.js`
    - `frontend/public/widget/agentnexlify-widget.js`
    - `landing-page-v2/widget/agentnexlify-widget.js`
  - Fix: Canonical source = `frontend/public/widget/`. Others → symlinks or build step. (Note: CLAUDE.md already requires byte-identical — the issue is 3 manual copies, not a policy gap.)

- [ ] **Analytics Router (2,023 lines) — Mixed Concerns** | Pass 1 | Effort: M
  - 60+ endpoints covering dashboard metrics, agent control center, tenant stats, recovery analytics, wizard tracking.
  - Fix: Split into `dashboard_analytics.py`, `agent_analytics.py`, `recovery_analytics.py`.

- [ ] **Auth Router (1,908 lines) — Mixed Concerns** | Pass 1 | Effort: M
  - JWT validation + branding logic co-located. Security layer doing business logic.
  - Fix: Move branding to `branding_service.py`. Keep auth.py pure: JWT, tenant isolation, OAuth.

- [ ] **Twilio SDK Stale (9.4.0 → 10.x available)** | Pass 5 | Effort: S
  - `backend/requirements.txt:14` pins `twilio==9.4.0` (~2 years old).
  - Fix: Upgrade to `twilio>=10.0.0,<11` after SMS integration test.

---

## MEDIUM (tech debt backlog)

- [ ] **N+1 in `check_no_response_leads()`** | Pass 6 | Effort: M
  - `automation_engine.py:759-791` — per-lead call to `trigger_sequence()`, which makes independent DB queries per lead.
  - Fix: Batch trigger + bulk enrollment insert.

- [ ] **Widget Helpers Router (1,632 lines)** | Pass 1 | Effort: M
  - `backend/routers/widget_helpers.py` — chat, lead capture, booking helpers, callback logging all mixed.
  - Fix: Split into `widget_chat_router.py`, `widget_booking_router.py`, `widget_lead_capture_router.py`.

- [ ] **Local SEO Router (1,552 lines)** | Pass 1 | Effort: S
  - Coherent domain but growing. Monitor; plan split at 2,000 lines.

- [ ] **Invoices Router (1,206 lines)** | Pass 1 | Effort: S
  - CRUD + PDF generation + recurring logic mixed.
  - Fix: Extract `invoice_service.py` for recurring + PDF. Router handles CRUD only.

- [ ] **Calls Router (1,176 lines)** | Pass 1 | Effort: S
  - Twilio webhook handling + AI call routing + transcription mixed.
  - Fix: Extract `call_handler_service.py`. Router handles webhooks only.

- [ ] **Stale Event Name `"lead_stage_change"`** | Pass 4 | Effort: S
  - `automation_engine.py:31` — event name references old `lead_stage` nomenclature; schema uses `status`.
  - Fix: Rename to `"lead_status_change"` for consistency.

---

## LOW (nice to have)

- [ ] **Monolithic Test Files** | Pass 1 | Effort: L
  - `backend/tests/test_managed_agents.py` (1,331 lines)
  - `tests/test_automation_engine.py` (1,099 lines)
  - Fix: Split by feature group. No urgency.

- [ ] **Frontend Packages** | Pass 5 | Effort: S
  - React 18.3.1, React Router 7.13.1, Vite 6.4.2 — all current.
  - Fix: Quarterly `npm audit` + major version pin review.

---

## Stats

| Metric | Count |
|--------|-------|
| Files >600 lines | 19 |
| Layer violations (service→router) | 4 files |
| Dead code candidates | 0 |
| Schema drift risks | 0 |
| N+1 candidates | 2 (high-severity) |
| CVEs (C/H/M) | 0/0/0 |
| Sync-in-async issues | 0 |

**Largest files:** `automation_engine.py` (4,285) · `analytics.py` (2,023) · `auth.py` (1,908) · `widget_helpers.py` (1,632) · `local_seo.py` (1,552)

---

## Recommended execution order

1. **This session**: Fix Anthropic SDK pin (1 line, `requirements.txt:4`) — S effort, CRITICAL
2. **Next session**: Service→router import violations (4 files, extract shared utilities) — M effort, CRITICAL
3. **Sprint**: Split `automation_engine.py` god class — L effort, HIGH, use compound-engineering pipeline
4. **Sprint**: Fix both N+1 patterns in automation_engine — M effort, CRITICAL+MEDIUM
5. **Backlog**: Router splits (analytics, auth, widget_helpers, invoices, calls) — M effort each, HIGH/MEDIUM
