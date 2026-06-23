# Architecture Health Report — 2026-06-23

Audit-only structural review of AgentNexLiFy per `.claude/skills/improve-architecture/SKILL.md` six passes. No source files changed. Findings ranked by severity with file:line, effort (S/M/L), and suggested fix.

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 5 |
| MEDIUM | 8 |
| LOW | 6 |

### Stats
- Files >600 lines: 38 (22 frontend, 13 backend non-test, 2 widget copies, plus 3 test files)
- Schema-drift CRITICAL hits (`tenant_id`/`lead_stage`/`service_interest` on leads/conversations): **0**
- Layer violations (services importing routers): 5 (all documented god-split helper extractions)
- Dead-router candidates: 0 (all 4 "not-in-main" files are imported helpers)
- N+1 candidates: 3 (2 seed-only, 1 minor)
- Sync-blocking-in-async hotspot: 1 (widget `/chat` — high signal)
- Unpinned deps: backend 3 fully-floating, frontend all `^`-ranged

### Schema-discipline verdict (Pass 4) — CLEAN
The recurring production-bug invariants hold. `leads` and `conversations` are queried with `client_id` everywhere (sms.py:54/102/120, csat.py:70, widget_booking.py:434, conversations_service.py, mcp_server.py:247/251). Every `tenant_id` hit is on a **different** table where `tenant_id` is the real column (`chat_messages`, `documents`, `scoring_configs`, `menu`, `csat`, `webhook_deliveries`). `lead_stage` appears only as an automation **event name** (`lead_stage_change`), never a column. `service_interest` appears only as a Python parser var/key that is mapped to the `areas_of_interest` column (leads.py:538, widget_lead_helpers.py:415-417). No drift. No fix needed.

---

## HIGH (fix this sprint)

- [ ] **Sync Supabase calls block the event loop in the hottest path** — `backend/routers/widget_chat.py:313` (`async def widget_chat`) makes ~16 synchronous `db.table(...).execute()` calls (e.g. lines 364, 404, 425, 691, 708, 728, 764, 838, 1136) directly in the async handler. The Supabase Python client is blocking (no `await db.table` anywhere; `get_service_supabase` returns sync `create_client`). Every widget message serializes DB I/O on the loop, capping concurrency. The LLM call is correctly offloaded (`await call_claude_messages` → `run_in_executor`), so DB is the remaining blocker. | Pass 6 | Effort: L | Fix: wrap the per-request DB reads in `run_in_threadpool(...)` (already imported lazily at line 131) or batch into fewer round-trips; longer-term, move read-heavy widget queries behind a thin service that the handler awaits via threadpool.

- [ ] **`widget_chat.py` god file (1332 lines) on a hard-stop surface** — `backend/routers/widget_chat.py:1` already spun out `widget_chat_helpers.py` (1122) and `widget_lead_helpers.py` (824), yet the router itself is still 2.2x the 600-line threshold and owns chat routing + rate limiting + team-reply detection + flow execution + FAQ/menu/jobs/forms lookups. Widget changes are a CLAUDE.md hard-stop (byte-identical rule, grill-me gate). | Pass 1 | Effort: L | Fix: extract the per-feature context lookups (FAQ/menu/jobs/forms/flow at lines ~691-838) into a `widget_context_service.py`; keep the router as orchestration only.

- [ ] **`onboarding.py` god file (1364 lines) with repeated FAQ-insert loops** — `backend/routers/onboarding.py:671`, `:689`, `:962`, `:1088` each build/insert FAQ rows in near-duplicate blocks. Largest backend router; mixes preset seeding, AI content generation, and FAQ persistence. | Pass 1 + Pass 6 | Effort: L | Fix: factor a single `_persist_faqs(tenant_id, faqs)` helper (the :689 path inserts one-row-per-loop — batch it like :671 does), then split preset vs AI-content concerns into modules.

- [ ] **`schemas.py` is a 1010-line shared model dumping ground** — `backend/models/schemas.py:1`. A single import touched by nearly every router; changes here have wide blast radius and merge-conflict risk (user-rules Rule 9/12). | Pass 1 | Effort: M | Fix: split by domain (`schemas/leads.py`, `schemas/billing.py`, `schemas/widget.py`, …) behind a `schemas/__init__.py` re-export so existing imports keep working — staged, no half-migration.

- [ ] **`invoices.py` (1243) lazy-imports `python-dateutil` in a hot path** — `backend/routers/invoices.py` plus `automation/scheduled_jobs_ext.py` rely on a lazy `relativedelta` import; the dep was only added to `requirements.txt` on 2026-06-23 (untracked-deps audit). Until that pin ships everywhere, those paths 500 on a clean deploy. Same class as the documented PyYAML/qrcode incidents. | Pass 5 | Effort: S | Fix: confirm the new `python-dateutil>=2.8,<3` pin is deployed to Railway prod, then add a smoke test that imports the scheduled-jobs module on the boot path.

---

## MEDIUM (tech debt backlog)

- [ ] **Frontend page god files** — `LocalSEOPage.jsx` (2253), `IntegrationsPage.jsx` (2066), `ConversationsPage.jsx` (2039), `LeadDetailDrawer.jsx` (1688), `WidgetPage.jsx` (1398), `DocumentsPage.jsx` (1311), `LeadsPage.jsx` (1206). | Pass 1 | Effort: L | Fix: extract sub-sections into child components + co-located hooks; start with `LocalSEOPage.jsx`.
- [ ] **`demo_seed.py` (1719) row-by-row insert N+1** — `backend/services/demo_seed.py:1487` (leads), `:1515` (appointments), `:1425` (FAQs) loop single-row inserts. Seed-only path, not user-facing, but slow on demo reset. | Pass 6 | Effort: M | Fix: collect rows and bulk-insert per table (the pattern at pipeline_presets.py:115 is the model).
- [ ] **`main.py` wires 103 `include_router` calls in one 1040-line file** — `backend/main.py:1`. Registration sprawl; easy to drop a router silently (the fastapi/starlette pin comment shows this already bit once). | Pass 1 | Effort: M | Fix: group router registration into `backend/routers/registry.py` returning a list, loop-register in main.
- [ ] **`leads.py` (1176) + `LeadsPage.jsx` (1206) parallel bloat** — core lead domain is heavy on both ends. | Pass 1 | Effort: M | Fix: split leads router into read vs write vs enrichment modules.
- [ ] **Cross-router private-symbol imports** — `team.py:20` and `auth_demo.py:24` reach into `auth.py` for `_create_token`/`_hash_password`/`_jwt_secret` (underscore-private). `zapier.py:28` imports `_get_current_tenant`. Works, but couples routers to each other's internals. | Pass 2 | Effort: M | Fix: promote shared auth primitives into `backend/services/auth_core.py`; routers import the service, not each other.
- [ ] **`billing.py` ↔ `stripe_webhooks.py` circular-ish coupling** — `stripe_webhooks.py:17` imports from `billing.py`, and `billing.py:246` lazy-imports back from `stripe_webhooks.py`. The lazy import is the tell of a cycle worked around at runtime. | Pass 2 | Effort: M | Fix: extract the shared invoice-handling logic into a `billing_core` service both import one-directionally.
- [ ] **`time.sleep` retry backoff in `managed_agents.py`** — `backend/services/managed_agents.py:145/187/503/526`. Safe only if every caller runs off the loop. `llm_runtime.py:316` is correctly inside the sync variant offloaded via executor; `managed_agents.py` should be audited the same way. | Pass 6 | Effort: S | Fix: confirm all callers go through threadpool/executor, or switch to `asyncio.sleep` in async callers.
- [ ] **Fully-unpinned backend deps** — `backend/requirements.txt`: `email-validator`, `bcrypt`, `google-auth`/`google-auth-oauthlib`/`google-api-python-client` have lower bounds only, no upper cap. Most of the file is well-disciplined with documented ranges. | Pass 5 | Effort: S | Fix: add upper bounds (`<3`, `<5`, `<3` respectively) to match the file's existing convention.

---

## LOW (nice to have)

- [ ] **`widget_booking_helpers.py` (23 lines) imported by 0 files** — `backend/routers/widget_booking_helpers.py:1`. Truly orphaned (the other 3 "not-in-main" routers are imported helpers; this one is not imported anywhere). | Pass 3 | Effort: S | Fix: verify via `gitnexus_impact`, then delete or fold into `widget_booking.py`.
- [ ] **`verticals.js` (1036) is a flat data blob in `pages/`** — `frontend/src/pages/verticals/verticals.js`. Config data living under pages. | Pass 1 | Effort: S | Fix: move to `frontend/src/data/` or split per vertical.
- [ ] **Frontend `vite ^8` / `vitest ^4` floating majors** — `frontend/package.json`. Caret on build tooling majors invites surprise breakage. | Pass 5 | Effort: S | Fix: pin exact versions for build/test tooling, keep `^` on runtime libs only.
- [ ] **`scheduled_jobs_ext.py` (931) near threshold** — `backend/services/automation/scheduled_jobs_ext.py`. Watch list; the digest/os_opportunities seam is correctly kept separate per audit note — do not merge it. | Pass 1 | Effort: M | Fix: split additional scheduled-job families into `scheduled/` submodules (pattern already started in `scheduled/`).
- [ ] **`rule_engine.py` (875) + `AutomationRulesPage.jsx` (972)** — automation domain heavy both ends. | Pass 1 | Effort: M | Fix: backlog split.
- [ ] **`test_managed_agents.py` (1374) / `test_os_actions.py` (1110) / `test_value_digest.py` (843) large test files** — not production risk, but slow to navigate. | Pass 1 | Effort: S | Fix: split by scenario class when next touched.

---

## After the Report
Per the skill, hand items off in a **separate** session (do not fix + audit together):
- HIGH #1 (widget sync DB) → `performance-optimizer` + `widget-specialist` (widget-test gate after).
- HIGH #2/#3/#4 god splits → `god-class-splitter` skill, note split axis in `plans/god-class-refactor_plan.md`.
- HIGH #5 + MEDIUM dep caps → `dependency-auditor` skill.
- LOW #1 orphan file → `dead-code-sweep` skill (verify with `gitnexus_impact` first).
