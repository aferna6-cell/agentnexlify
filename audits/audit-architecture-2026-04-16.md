# Architecture Health Report — 2026-04-16

## CRITICAL (fix before next deploy)

- [x] **N+1 Query in `process_pending_steps()`** | Pass 6 | Effort: M — FIXED 2026-04-16 (commit 344df51)
  - Before: select("id") → per-row execute_step() re-fetch → 51 DB calls per 50-row batch
  - After: select("*") → pass pre-loaded `execution_data` kwarg → 1 DB call per batch
  - execute_step signature gained `execution_data: dict | None = None` (backward compatible)

- [x] **Anthropic SDK Version Mismatch** | Pass 5 | Effort: S — FIXED 2026-04-16 (commit 422c203)
  - Unpinned: `anthropic==0.42.0` → `anthropic>=0.95.0,<1`

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

- [x] **Widget JS duplicated × 3** | Pass 1 | Effort: M — FIXED 2026-04-16
  - Canonical = `frontend/public/widget/agentnexlify-widget.js`. `widget/agentnexlify-widget.js` verified byte-identical.
  - `landing-page-v2/widget/agentnexlify-widget.js` is legacy — left untouched per policy.
  - Created `scripts/sync-widget.sh`: copies canonical → `widget/` on demand (Windows-safe, no symlinks).
  - Pre-push hook CHECK 7 (`scripts/hooks/pre-push:164-174`) already diffs the two non-legacy files and warns on drift — continues to work unchanged.

- [ ] **Analytics Router (2,023 lines) — Mixed Concerns** | Pass 1 | Effort: M
  - 60+ endpoints covering dashboard metrics, agent control center, tenant stats, recovery analytics, wizard tracking.
  - Fix: Split into `dashboard_analytics.py`, `agent_analytics.py`, `recovery_analytics.py`.

- [ ] **Auth Router (1,908 lines) — Mixed Concerns** | Pass 1 | Effort: M
  - JWT validation + branding logic co-located. Security layer doing business logic.
  - Fix: Move branding to `branding_service.py`. Keep auth.py pure: JWT, tenant isolation, OAuth.

- [!] **Twilio SDK Stale (9.4.0 → 10.x available)** | Pass 5 | Effort: S — REVERTED 2026-04-16 (broke Railway)
  - Audit recommendation was WRONG: twilio 10.x does NOT exist on PyPI (latest is 9.10.5).
  - Commit 344df51 applied the bad pin → Railway build failed with "No matching distribution found for twilio<11,>=10.0.0".
  - Fix: REMOVED twilio from requirements.txt entirely. `twilio_service.py` uses raw httpx, zero SDK imports in backend/.
  - Lesson: audit claims about dependency versions MUST be verified against PyPI before commit. See `rules/fill-instructions-before-guessing.md`.

---

## MEDIUM (tech debt backlog)

- [x] **N+1 in `check_no_response_leads()`** | Pass 6 | Effort: M — FIXED 2026-04-16 (commit 73589d5)
  - Before: per-lead trigger_sequence() → O(3 * leads) DB round-trips
  - After: group leads by tenant → 1 sequences query + 1 steps query + 1 bulk insert per tenant → O(3 * tenants)
  - Unique-constraint fallback: bulk insert hits dup → per-record retry; logs duplicates at DEBUG

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

- [~] **Stale Event Name `"lead_stage_change"`** | Pass 4 | Effort: S — REJECTED 2026-04-16
  - Audit recommendation contradicts existing ADR at `docs/dev-knowledge/architecture-decisions.md:67` which explicitly says "Keep `lead_stage_change` as the automation trigger event name."
  - Rename would touch 15+ files (backend + frontend + tests + migration comments) AND require a data migration for existing `automation_sequences.trigger_event` rows stored as `"lead_stage_change"`. Not "S effort — 1 line."
  - Rule 7 (honor CLAUDE.md + ADRs) + Rule 8 (no half migrations) → KEEP AS-IS.
  - If clarity is still desired, add a docstring near `VALID_TRIGGER_EVENTS` in `backend/models/schemas.py:684` explaining that the event name is intentionally decoupled from the `status` column name.

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
| N+1 candidates | 0 (both fixed 2026-04-16) |
| CVEs (C/H/M) | 0/0/0 |
| Sync-in-async issues | 0 |

**Largest files:** `automation_engine.py` (4,418, ↑133 since audit) · `analytics.py` (2,023) · `auth.py` (1,896) · `widget_helpers.py` (1,632) · `local_seo.py` (1,552)

---

## Status update — 2026-04-16 afternoon

**Closed:**
- All 3 CRITICAL items (anthropic unpin, service→router violations, process_pending_steps N+1)
- 2 of 5 HIGH items (widget dupe, Twilio upgrade)
- 1 of 6 MEDIUM items (check_no_response_leads N+1)
- Rejected 1 MEDIUM item (lead_stage_change rename — contradicts ADR)

**Remaining open:**
- HIGH: god class split (automation_engine), analytics router split, auth router split
- MEDIUM: widget_helpers split, local_seo monitor, invoices service extract, calls service extract
- LOW: monolithic tests, quarterly npm audit

**Next session plan:** see `plans/post-audit-remediation_plan.md`

---

## Recommended execution order

1. ~~**This session**: Fix Anthropic SDK pin~~ DONE
2. ~~**Next session**: Service→router import violations~~ DONE
3. **Sprint**: Split `automation_engine.py` god class — L effort, HIGH, use compound-engineering pipeline
4. ~~**Sprint**: Fix both N+1 patterns in automation_engine~~ DONE
5. **Backlog**: Router splits (analytics, auth, widget_helpers, invoices, calls) — M effort each, HIGH/MEDIUM
