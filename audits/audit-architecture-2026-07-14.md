# Architecture Health Report — 2026-07-14

Audit-only structural review per `.claude/skills/improve-architecture/SKILL.md` six passes. No source files changed. Ranked by severity with file:line, effort (S/M/L), one-line fix. Extra attention on yesterday's surfaces: voice (calls/routing/metering), tenant KB (upload/Drive/sync-token/local CLI), OS chat (connector awareness), widget.

Method note: run in a detached working copy, so "grew yesterday" attribution came from `docs/dev-knowledge/schema-log.md` dated entries (164, 165 = 2026-07-13) plus feature-named files; line counts via `rg -c '^'`.

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 4 |
| MEDIUM | 6 |
| LOW | 4 |

### Stats
- Files >600 lines: 50 (26 frontend incl. 1 data blob, 19 backend routers, 5 backend services). New KB/connector code is well-factored (all <420 lines) — no new god files from yesterday.
- Schema-discipline (Pass 4) invariant check: **CLEAN**. All 3 new tables (`tenant_integrations`, `integration_sync_log`, `tenant_kb_documents`) use `client_id`. `connector_awareness` correctly splits `integrations`→tenant_id, `tenant_integrations`→client_id, `tenants`→id, `tenant_api_keys`→tenant_id. `compile_tenant_kb` writes `widget_configs` on `tenant_id` (correct per migration 077). No `tenant_id`/`lead_stage`/`service_interest` drift.
- Migrations without schema-log entries: 7 (154–159, 163).
- Layer violations (service→router imports): 3 (control_center trio → `analytics._common`).
- Dead-code candidates: 1 (`widget_booking_helpers.py`, carryover).
- Sync-DB-in-async hotspots in yesterday's code: 3 write surfaces + 1 read path.

### Positive notes (yesterday's work)
- Cron Drive sync is correctly offloaded: `backend/main.py:352-354` wraps `run_drive_kb_sync_due` in `asyncio.to_thread`.
- Voice routing fixed the latent scan bug: `calls.py:163-171` now does an exact indexed `twilio_number` lookup (migration 164) instead of the old `limit(50)` scan.
- No new dependencies added — `drive_kb_sync` deliberately uses already-pinned `httpx` over `googleapiclient`; `tenant_kb` uses already-pinned `pypdf`/`python-docx`.

---

## HIGH (fix this sprint)

- [ ] **H1 — Drive KB sync blocks the event loop on user-facing endpoints** — `backend/routers/kb_integrations.py:160`, `:163`, `:171`. `/folder` and `/sync-now` call `sync_tenant_drive()` directly inside `async def` handlers. That function (`drive_kb_sync.py:289`) makes blocking `httpx` calls (folder list + per-file fetch/export, timeouts up to 60s each at `:278`) plus sequential DB writes plus a compile — all on the request worker's event loop. The cron path was offloaded (`main.py:352`) but these two interactive endpoints were not. First-folder-set on a large folder can stall a worker for many seconds. | Pass 6 | Effort: M | Fix: `await run_in_threadpool(sync_tenant_drive, tenant_id)` in both handlers.
- [ ] **H2 — Bulk KB upload + recompile block the event loop** — `backend/routers/tenant_kb.py:130-177` (`upload_documents`) loops up to 100 files calling sync `ingest_file` (extract + select + insert/update per file) then sync `compile_tenant_kb`, all on the async loop; `:199` (delete) and `:210` (recompile) also compile synchronously in-request. A 100-file drag-drop serializes ~200 blocking DB round-trips + PDF parsing on one worker. | Pass 6 | Effort: M | Fix: offload the per-batch ingest+compile via `run_in_threadpool`; return a job/summary rather than blocking the request.
- [ ] **H3 — `calls.py` god file (1172 lines), voice hard-surface, expanded yesterday** — `backend/routers/calls.py:1`. 1.95x the 600-line threshold; owns phone routing, TwiML webhooks, G3 metering (`minutes_this_month`/`included_minutes` at `:130`), and booking. Voice + Twilio webhook changes are high-blast-radius (signature verify, tenant routing). | Pass 1 | Effort: L | Fix: split webhook handlers, the `_find_tenant_by_phone` routing helper, and G3 metering into separate modules; keep `calls.py` as route wiring.
- [ ] **H4 — `widget_chat.py` god file (1332 lines) still 2.2x threshold on the hottest path** — `backend/routers/widget_chat.py:1` (carryover from 2026-06-23 HIGH). Already spun out `widget_chat_helpers.py` (1124) + `widget_lead_helpers.py` (824) yet the router still owns routing + rate-limit + team-reply detect + flow/FAQ/menu/jobs/forms lookups. Widget is a CLAUDE.md hard-stop. | Pass 1 | Effort: L | Fix: extract per-feature context lookups into `widget_context_service.py`; router = orchestration only.

---

## MEDIUM (tech-debt backlog)

- [ ] **M1 — Connector-awareness adds up to 4 sync Supabase queries per OS chat turn on the event loop** — `backend/services/connector_awareness.py:104-161` (`connection_status`) runs four sequential blocking `db.table(...).execute()` calls, invoked from `os_thread_runner.process_user_turn` (`os_thread_runner.py:82`, `async`) with no threadpool offload, awaited from the request path at `os_threads.py:174`. Only fires on a regex inference hit, but compounds the systemic sync-Supabase-in-async pattern (2026-06-23 HIGH #1). | Pass 6 | Effort: M | Fix: batch the status lookups behind one `run_in_threadpool`, or collapse to a single query per source.
- [ ] **M2 — Services import from a router package (layer inversion)** — `backend/services/control_center_service.py:8`, `control_center_fetch.py:6`, `control_center_scoring.py:5` all import from `backend.routers.analytics._common` (`_QUERY_LIMIT`, `_period_to_days`, `_build_control_center_recommendations`). Services depending on routers inverts the layer boundary. | Pass 2 | Effort: M | Fix: move the shared constants/helpers into a `backend/services/analytics_common.py`; routers and services both import downward.
- [ ] **M3 — 7 migrations have no schema-log.md entry** — migrations `154_conversation_sentiment_intent`, `155_kb_articles_fts`, `156_error_events`, `157_referral_clicks`, `158_wizard_events_fix_step_range`, `159_tenant_referred_by_widget_key`, `163_booking_enabled_default_true` exist in `migrations/` but have no matching `## NNN_` header in `docs/dev-knowledge/schema-log.md` (yesterday's 164/165 are correctly logged). Violates the migration workflow rule (migrate → apply → update schema-log). | Pass 4 | Effort: S | Fix: backfill 7 log entries; add a CI check that every `migrations/NNN_*.sql` has a schema-log header.
- [ ] **M4 — Backend router god files beyond the voice/widget hot paths** — `onboarding.py` (1550), `invoices.py` (1243), `leads.py` (1185), `email_sequences.py` (1143), `booking_page.py` (1065), `auth.py` (992), `billing.py` (949). | Pass 1 | Effort: L | Fix: staged splits behind re-export `__init__` (start with `onboarding.py` preset-vs-AI-content seam).
- [ ] **M5 — Frontend page god files** — `LocalSEOPage.jsx` (2253), `IntegrationsPage.jsx` (2066), `ConversationsPage.jsx` (2039), `Dashboard/LeadDetailDrawer.jsx` (1686), `WidgetPage.jsx` (1398), `DocumentsPage.jsx` (1311), `Home.jsx` (1047), `Dashboard/OnboardingChecklist.jsx` (1003). | Pass 1 | Effort: L | Fix: extract child components + co-located hooks; start with `LocalSEOPage.jsx`.
- [ ] **M6 — Fully-unpinned backend deps (no upper bound)** — `backend/requirements.txt:13,29,33,34,35`: `email-validator>=2.0.0`, `bcrypt>=4.0.0`, `google-auth>=2.0.0`, `google-auth-oauthlib>=1.0.0`, `google-api-python-client>=2.0.0`. The Google trio now underpins the Drive KB OAuth path shipped yesterday, raising the surprise-major-bump risk. Rest of the file is disciplined with ranges. | Pass 5 | Effort: S | Fix: add upper caps (`<3`, `<5`, `<3`, `<2`, `<3`) matching file convention.

---

## LOW (nice to have)

- [ ] **L1 — `widget_booking_helpers.py` (23 lines) imported by 0 files** — `backend/routers/widget_booking_helpers.py:1`. Zero import sites in `backend/` (grep clean). Carryover orphan from 2026-06-23, still unfixed. | Pass 3 | Effort: S | Fix: verify with `gitnexus_impact`, then delete or fold into `widget_booking.py`.
- [ ] **L2 — Frontend build-tooling floating majors** — `frontend/package.json`: `vite ^8`, `vitest ^4`, `jsdom ^29`, `react-router-dom ^7`, `recharts ^3`. Caret on tooling/runtime majors invites surprise breakage. | Pass 5 | Effort: S | Fix: pin exact for build/test tooling; keep `^` on runtime libs only.
- [ ] **L3 — Backend service god files** — `demo_seed.py` (1719, seed-only, row-by-row insert N+1), `automation/scheduled_jobs_ext.py` (931), `automation/rule_engine.py` (875), `local_seo_execute.py` (674), `booking.py` (654). | Pass 1 | Effort: M | Fix: backlog splits; bulk-insert the `demo_seed` loops.
- [ ] **L4 — Voice phone-routing fallback repeats the latent scan-cap bug at a higher ceiling** — `backend/routers/calls.py:179-199`. The exact `twilio_number` lookup is correct, but the fallback loads `.limit(200)` tenants and linear-scans `notification_phone`. Past 200 legacy tenants it silently misses the same way `limit(50)` did at #51 — bug class deferred, not removed. | Pass 6 | Effort: S | Fix: replace the scan with an indexed `notification_phone` suffix match, or a covering query; drop the in-memory loop.

---

## After the Report — do NOT fix in this session
Per `.claude/rules/daily-skills.md` (§5) and `improve-architecture`, **audit and fix are separate sessions** — mixing them causes half-finished refactors (user-rules Rule 8). This report is the deliverable; no fixes were started. Hand off in fresh sessions: H1/H2/M1 (sync-in-async) → `performance-optimizer`; H3/H4/M4/M5 god splits → `god-class-splitter` (one split axis per PR, no half-migrations); M3 → schema-log backfill + CI gate; M6/L2 → `dependency-auditor`; L1 → `dead-code-sweep` after `gitnexus_impact`.
