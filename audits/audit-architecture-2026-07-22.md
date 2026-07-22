# Architecture Health Report - 2026-07-22

Audit-only structural review per `.claude/skills/improve-architecture/SKILL.md` six passes. No source files changed; this file is the only write. Extra attention on the ~15 merged "Agent OS suite" PRs (os_* routers/services, plan gate, email actions, projects, research). Line counts via `wc -l`; all grep evidence reproduced below. ADRs skimmed (`docs/dev-knowledge/architecture-decisions.md`, 8 ADRs through 2026-07-22-001) - no recommendation below contradicts one.

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 7 |
| LOW | 4 |

- Files >600 lines (non-test): 55, up from 50 on 2026-07-14. New os_* backend code is well factored (21 routers all <500 lines; only `os_inbound_bridge.py` crosses 600).
- Prior-audit wins confirmed: `widget_chat.py` split landed (485 lines, was 1332 - 07-14 H4 resolved); `analytics_common.py` moved to services (07-14 M2 resolved); no service imports any router today.
- Schema-discipline invariants: CLEAN (see "Not broken" list).

## Ranked Findings

| ID | Sev | Pass | Finding | Effort |
|----|-----|------|---------|--------|
| H1 | HIGH | 2/6 | Agent OS plan gate applied to only 9 of 21 os_* routers | M |
| H2 | HIGH | 1 | `calls.py` god file carryover, grew to 1196 lines | L |
| M1 | MED | 6 | Mock DB helpers copy-pasted 4x across round test suites, already drifting | S |
| M2 | MED | 6 | `cardStyle`/`btnStyle` duplicated in 4 os components; OpportunityCards hardcodes hex | S |
| M3 | MED | 6 | `_INBOUND_THREAD_SOURCES` set duplicated in 2 services | S |
| M4 | MED | 4 | Migrations 185, 186 missing from schema-log; `[skip ci]` bypasses the CI gate | S |
| M5 | MED | 2 | os components call `fetch()` directly instead of `utils/api/os.js` | S |
| M6 | MED | 2 | Routers import auth/billing helpers from other routers | M |
| M7 | MED | 1 | Carryover god files, backend + frontend (13 files >900 lines) | L |
| L1 | LOW | 3 | `StripeTrialBanner.jsx` orphan, 0 importers | S |
| L2 | LOW | 4 | Migration number collisions 005 (x2) and 007 (x3), carryover | S |
| L3 | LOW | 1 | `os_inbound_bridge.py` at 638 lines, just over threshold | M |
| L4 | LOW | 1 | `demo_seed.py` 1731 lines, seed-only carryover | M |

---

## HIGH

### H1 - Agent OS plan gate covers 9 of 21 os_* routers
`grep -c require_agent_os_access backend/routers/os_*.py`: gated (2 hits each) = os_ask_data, os_deliverables, os_instructions, os_mcp, os_orchestrate, os_projects, os_research, os_tasks, os_threads. Zero hits = os_agent_runs, os_backlog, os_files, os_graph, os_insights, os_memory, os_run_trace, os_sync, os_usage, os_usage_breakdown (plus os_inbound and os_email_actions, which are intentionally public webhook/token surfaces). The ungated ten authenticate with `Depends(_get_current_tenant)` only (e.g. `backend/routers/os_files.py:177`, `os_memory.py:40`, `os_graph.py:29`), so a `chatbot`-plan ($19.99) tenant can hit agent_os-only surfaces: file uploads, memory writes, graph reads, backlog, sync, run traces. `agent_os` is the $99.99 differentiator (CLAUDE.md plan gating).
Fix: decide per router which are genuinely shared, then add `dependencies=[Depends(require_agent_os_access)]` at router construction for the rest; add cases to `backend/tests/test_plan_gating_new_plans.py`. Effort: M.

### H2 - `calls.py` still a god file on the voice hard surface
`backend/routers/calls.py` = 1196 lines (2x the 600 threshold; 1172 at 07-14 audit, so it grew despite the `voice_call_summary.py`/`voice_twiml.py` extractions). Mixes Twilio webhook handling, tenant phone routing, metering, and booking. Carryover of 07-14 H3.
Fix: continue the started split (webhook handlers vs routing vs metering modules), one axis per PR per user-rules Rule 8/9. Effort: L.

---

## MEDIUM

### M1 - Round-suite mock helpers quadruplicated and drifting
`_run`/`_Result`/`_Query`/`_db` are copy-pasted in `backend/tests/test_suite_round3.py:19-49`, `test_suite_round4.py:15-44`, `test_suite_round5.py:16-46`, `test_workforce_round2.py:9-30`. They have already diverged: round3 `_Result.__init__(self, data, count=None)` vs round4 `_Result.__init__(self, data)` (diff verified). Next fake-supabase behavior fix must land in 4 places.
Fix: extract to `backend/tests/conftest.py` (or `backend/tests/_fake_supabase.py`) and import; keep the round3 superset signature. Effort: S.

### M2 - os card styles copy-pasted 4x plus one theme break
Identical `cardStyle` + `btnStyle` consts in `frontend/src/components/os/AskDataCard.jsx:7`, `ProjectsCard.jsx:16`, `ResearchCard.jsx:10`, `ScheduledTasksCard.jsx:13` (same `var(--bg-secondary, var(--card-bg))` block). `OpportunityCards.jsx:21` instead hardcodes `background: "#0f0f17"` and `:128` hardcodes `#3b82f6`, breaking theme-token consistency with its siblings.
Fix: one `frontend/src/components/os/osStyles.js` exporting the shared consts; switch OpportunityCards to the CSS vars. Effort: S.

### M3 - `_INBOUND_THREAD_SOURCES` defined twice
Identical set `{"widget", "email", "sms", "facebook", "instagram", "voice"}` at `backend/services/os_chat_projects.py:27` and `backend/services/os_thread_runner.py:47`. A new channel (e.g. whatsapp) added to one silently misroutes in the other.
Fix: single definition (thread_runner is the natural owner or a small `os_constants.py`); import in os_chat_projects. Effort: S.

### M4 - Migrations 185 and 186 have no schema-log entry
`migrations/185_photo_quote_feedback.sql` and `186_pending_automations.sql` exist; `grep -E "^##+ ?18[56]_" docs/dev-knowledge/schema-log.md` = 0 hits (178-184 all logged). The diff-based CI gate (`scripts/check_migration_schema_log.py`, added 2026-07-15 fixing 07-14 M3) did not catch these - team-contract commits carry `[skip ci]` (CLAUDE.md SHARED TEAM section), which skips the gate.
Fix: backfill 2 log entries; move the schema-log check into the pre-push hook so `[skip ci]` cannot bypass it. Effort: S.

### M5 - Agent OS components bypass the API layer
`frontend/src/components/os/OsInsightsCard.jsx:18` and `ComposerAttachments.jsx:50,77` call `fetch(...)` directly while sibling cards use `frontend/src/utils/api/os.js` (which exists and covers most os endpoints). Repo-wide there are 36 direct-fetch lines outside `utils/api` (some pre-auth pages are arguably fine), but these two are new this week and inconsistent with their own family.
Fix: add `fetchOsInsights`, `uploadOsAttachment`, `generateOsImage` to `utils/api/os.js`; swap call sites. Effort: S.

### M6 - Router-to-router helper imports
Cross-feature router imports where the helper belongs in a service or `backend/dependencies`: `zapier.py:28` and `team.py:20` and `auth_demo.py:24` import private auth helpers from `backend/routers/auth`; `stripe_webhooks.py:17` imports from `billing` while `billing.py:246` lazily imports back from `stripe_webhooks` (cycle avoided only by function-level import); `billing.py:561` imports `USAGE_PACK_TOKENS` from `billing_usage`; `admin_loop_health.py:27` from `admin_health`; `calls.py:29` from `automations`. (The `widget_chat_*` family imports are by-design helper modules from the H4 split - not counted.)
Fix: move `_hash_password`/`_create_token`/JWT consts into `backend/services/auth_core.py` (or `dependencies`), move the billing/webhook shared pieces into `backend/services/stripe_service.py`; routers import downward only. Effort: M.

### M7 - Carryover god files (07-14 M4/M5, unchanged or grown)
Backend: `onboarding.py` 1550, `widget_chat_helpers.py` 1351, `leads.py` 1185, `email_sequences.py` 1143, `booking_page.py` 1138, `auth.py` 1002, `billing.py` 949, `main.py` 1197, `models/schemas.py` 1018. Frontend: `LocalSEOPage.jsx` 2253, `ConversationsPage.jsx` 2071, `IntegrationsPage.jsx` 2066, `LeadDetailDrawer.jsx` 1686, `WidgetPage.jsx` 1398, `DocumentsPage.jsx` 1311, plus new-ish `AgentOS.jsx` 952 (os hub page - watch it; the suite PRs keep adding cards here).
Fix: staged splits via god-class-splitter, one file per PR; start with `onboarding.py` and `LocalSEOPage.jsx` as before. Effort: L.

---

## LOW

### L1 - `StripeTrialBanner.jsx` orphan
`frontend/src/components/StripeTrialBanner.jsx` (70 lines). `grep -rn StripeTrialBanner frontend/src frontend/index.html` returns only its own definition lines (2 self-hits, 0 importers).
Fix: delete, or wire it where the trial state is rendered if it was meant to ship. Verify with `gitnexus_impact` first. Effort: S.

### L2 - Migration number collisions (carryover)
`005_appointments.sql` + `005_automation_sequences.sql`; `007_google_calendar_integration.sql` + `007_team_members.sql` + `007_webhooks.sql`. Known since `audits/audit-schema-drift-2026-06-23.md` (which recommended renumbering the later-authored files); still unfixed. No numbering gaps otherwise (001-186 contiguous).
Fix: file-rename-only to next free numbers per the 06-23 audit; no re-apply. Effort: S.

### L3 - `os_inbound_bridge.py` at 638 lines
`backend/services/os_inbound_bridge.py` is the only Agent OS suite file over the 600 threshold. Bridges inbound email/sms/social into os threads; one concern, but at the Rule 9 line where the next addition should trigger a split (parse vs persist vs notify seams visible).
Fix: none now; split before extending. Effort: M when it fires.

### L4 - `demo_seed.py` 1731 lines (carryover 07-14 L3)
Seed-only path, row-by-row inserts. Unchanged. Backlog. Effort: M.

---

## Not broken, leave alone

- **Schema invariants CLEAN**: all `leads`/`conversations` queries spot-checked use `client_id` (e.g. `conversations_service.py:56,78,151`, `lead_scoring.py:310`); zero `lead_stage`/`service_interest` hits.
- **No real `from __future__ import annotations` in FastAPI files**: 46 grep hits are all docstring/comment mentions ("No from __future__ ... Rule 5") except `backend/tests/test_local_seo_handlers.py` - a test file, outside the invariant. Pre-commit CHECK 2 + pre-push CHECK 5 are in place.
- **Pass 4 table drift: zero** - every `.table("...")` name in backend appears in a `CREATE TABLE` in `migrations/` (comm of sorted sets is empty).
- **Backend services dead code: zero** - the 4 zero-importer candidates (`inbound_email_parser`, `inbound_email_verify`, `inbound_sms_verify`, `os_mcp_context`) are all imported via multi-line `from backend.services import (...)` blocks in `os_inbound.py:33-35`, `os_research.py:23`, `os_thread_runner.py:34`.
- **Dependency rot: none found** - every suspicious `requirements.txt` entry verified in use (`mcp` -> `backend/mcp_server.py:14`; google trio -> `services/google_calendar.py:7-11`; `pywebpush`, `qrcode`, `slowapi`, `python-jose` all hit). Twilio SDK correctly absent with tombstone comment. All 6 frontend `package.json` dependencies imported (react 153, react-router-dom 24, react-helmet-async 11, recharts 7, dompurify 2, react-dom 1).
- **07-14 fixes held**: `widget_chat.py` now 485 lines with clean helper-module split; no `backend/services/*` imports any router (only comments reference the old paths); `analytics_common.py` lives in services.
- **os_* plan-gate wiring pattern itself** is consistent where present (router-level `dependencies=[Depends(require_agent_os_access)]`) - H1 is about coverage, not mechanism.
- **`widget_chat_*`/`widget_booking` helper modules unregistered in `main.py`** - intentional (imported by `widget_chat.py`), not orphans.
- **os_inbound.py (486) and os_email_actions.py (131) ungated** - intentional public webhook/signed-token surfaces with their own verification (`inbound_email_verify.verify_postmark`, `verify_action_token`).
