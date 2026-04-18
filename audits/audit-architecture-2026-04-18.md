# Architecture Health Report — 2026-04-18

Weekly Monday cadence. Previous: 2026-04-16. Read-only audit — no fixes applied.

## CRITICAL (fix before next deploy)

_None._ No schema drift on `client_id`/`status`/`areas_of_interest`. No `from __future__ import annotations` in backend. Widget `widget/agentnexlify-widget.js` vs `frontend/public/widget/agentnexlify-widget.js` byte-identical (verified via `diff`, exit=0). No bare `except:` blocks.

---

## HIGH (fix this sprint)

- [ ] **Frontend god class: `SettingsPage.jsx` (2,262 lines)** | Pass 1 | Effort: L
  - `frontend/src/pages/SettingsPage.jsx:1` — single page handles profile, widget config, branding, billing, integrations, team, notifications, API keys.
  - Fix: Split into tab-panel components under `frontend/src/pages/Settings/` — `ProfilePanel.jsx`, `WidgetPanel.jsx`, `BrandingPanel.jsx`, `BillingPanel.jsx`, `IntegrationsPanel.jsx`, `TeamPanel.jsx`. Parent `SettingsPage.jsx` stays ≤200 lines as shell + tab routing.

- [ ] **Frontend god class: `ConversationsPage.jsx` (2,039 lines)** | Pass 1 | Effort: L
  - `frontend/src/pages/ConversationsPage.jsx:1` — list view, detail drawer, message composer, filters, bulk actions all inline.
  - Fix: Extract `components/Conversations/ConversationList.jsx`, `ConversationDetail.jsx`, `MessageComposer.jsx`, `ConversationFilters.jsx`.

- [ ] **Backend god class still open: `widget_helpers.py` (1,635 lines)** | Pass 1 | Effort: M
  - `backend/routers/widget_helpers.py:1` — carried over from 2026-04-16 audit (+3 lines since). Mixes chat assembly, lead capture, booking prep, callback logging, branding filters, prompt building.
  - Fix: Split into `widget_chat_helpers.py` (prompt + history), `widget_lead_helpers.py` (capture + enrichment), `widget_booking_helpers.py`. Current imports from `widget_helpers` in `widget_chat.py:26`, `widget_lead.py:20`, `widget_config.py:23`, `twilio_webhooks.py:238` need redirection.

- [ ] **Frontend god class: `LeadDetailDrawer.jsx` (1,688 lines)** | Pass 1 | Effort: M
  - `frontend/src/pages/Dashboard/LeadDetailDrawer.jsx:1` — drawer with 8+ tabs (timeline, notes, appointments, calls, docs, tasks, AI insights, custom fields).
  - Fix: One component per tab under `Dashboard/LeadDetail/`. Drawer shell wires them.

- [ ] **Backend god class: `auth.py` (1,416 lines)** | Pass 1 | Effort: M
  - `backend/routers/auth.py:1` — down 492 lines since 2026-04-16 (branding extracted), still large. Mixes JWT issuance, tenant bootstrap, OAuth flows, password reset, role gating, and 20+ routers import `_get_current_tenant` / `require_role` from here (27 cross-references found in Pass 2).
  - Fix: Extract `tenant_bootstrap.py` (signup + onboarding seed), `password_reset.py` (email-based reset flow), `oauth.py` (Google/Facebook). Keep `auth.py` as JWT + dependency helpers only. Cross-ref `docs/dev-knowledge/schema-log.md` pointer.

- [ ] **Migration numbering collisions: 005 + 007 have duplicates** | Pass 4 | Effort: S
  - `migrations/005_appointments.sql` vs `migrations/005_automation_sequences.sql`
  - `migrations/007_google_calendar_integration.sql` vs `007_team_members.sql` vs `007_webhooks.sql`
  - Risk: future `NNN_name.sql` naming rule (CLAUDE.md) already violated. New contributors will repeat.
  - Fix: Document exception in `docs/dev-knowledge/schema-log.md` (historical, do not renumber — breaks `supabase migrations` replay). Enforce strict sequential check in `scripts/hooks/pre-commit` for numbers ≥106.

- [ ] **Supabase MCP unauthorized — schema drift cross-check skipped** | Pass 4 | Effort: S
  - `mcp__supabase__list_tables` + `list_migrations` returned "Unauthorized. Please provide a valid access token" this session.
  - Fix: Verify `SUPABASE_ACCESS_TOKEN` env in Claude Code startup context; re-run cross-check next session. Per `rules/fill-instructions-before-guessing.md` — record as blocker, do not route around.

---

## MEDIUM (tech debt backlog)

- [ ] **Frontend pages 1,000-1,600 lines** | Pass 1 | Effort: M (each)
  - `EmailSequencesPage.jsx` (1,554), `LocalSEOPage.jsx` (1,525), `WidgetPage.jsx` (1,398), `DocumentsPage.jsx` (1,311), `FormBuilderPage.jsx` (1,306), `Home.jsx` (1,254), `LeadsPage.jsx` (1,206), `BidsPage.jsx` (1,132), `ABTestsPage.jsx` (1,119), `SmartListsPage.jsx` (1,114), `SequenceBuilder.jsx` (1,044), `ContentRepurposePage.jsx` (1,027), `SocialMediaPage.jsx` (1,019), `OnboardingChecklist.jsx` (1,003).
  - 14 pages between 1,000-1,600 lines. Per Rule 9, not yet god class but trending.
  - Fix: Monitor. Split opportunistically when next feature lands on the page (Rule 12 — new file default).

- [ ] **Backend routers 1,000-1,600 lines** | Pass 1 | Effort: M (each)
  - `local_seo.py` (1,552), `auth.py` (1,416 — also HIGH), `invoices.py` (1,211), `leads.py` (1,158), `calls.py` (1,175), `widget_chat.py` (1,065), `email_sequences.py` (1,065), `booking_page.py` (1,065), `onboarding.py` (1,054).
  - `invoices.py` + `calls.py` still have service-extract recommendations carried from 2026-04-16 audit (CRUD vs PDF/webhook mixing).

- [ ] **`scheduled_jobs_ext.py` (792 lines) vs `scheduled_jobs.py` (74 lines)** | Pass 1 | Effort: M
  - `backend/services/automation/scheduled_jobs_ext.py:1` — "ext" suffix implies companion to a small main. Real content is in ext. Naming inversion.
  - Fix: Rename `scheduled_jobs_ext.py` → canonical module name (e.g. `scheduled_jobs_impl.py`); merge the 74-line `scheduled_jobs.py` into it OR move into `scheduled/` package alongside `appointment_jobs.py`, `billing_jobs.py`, etc. that already exist.

- [ ] **`branding_service.py` (609 lines)** | Pass 1 | Effort: S
  - `backend/services/branding_service.py:1` — extracted from `auth.py` on 2026-04-16 (32KB). Just over god-class line. Handles branding + FAQ + website-content summary + widget-config stats.
  - Fix: Split FAQ CRUD into `faq_service.py`; stats-aggregation lines 532-572 belong in analytics.

- [ ] **`main.py` at 907 lines, Rule 9 threshold** | Pass 1 | Effort: S
  - `backend/main.py:1` — 907 lines; most weight is router registration (lines 746-813 per CLAUDE.md). Shape is OK but single-file registration will hit 1k soon.
  - Fix: Extract `backend/router_registry.py` with `register_routers(app)` function; `main.py` keeps startup/middleware.

- [ ] **`schemas.py` at 996 lines** | Pass 1 | Effort: S
  - `backend/models/schemas.py:1` — central Pydantic models. Domain-scoped splits would help grep.
  - Fix: Split by domain — `schemas/leads.py`, `schemas/widget.py`, `schemas/automation.py`, `schemas/billing.py`. Re-export from `schemas/__init__.py` for back-compat.

- [ ] **`rule_engine.py` (875 lines)** | Pass 1 | Effort: M
  - `backend/services/automation/rule_engine.py:1` — single-concern but growing. Monitor.

- [ ] **`managed_agents.py` (21.6 KB, `time.sleep` retry loops)** | Pass 6 | Effort: S
  - `backend/services/managed_agents.py:145, 187, 503, 526` — `time.sleep(wait)` in what may be async call paths (file is 21.6 KB; needs inspection). Also `backend/services/llm_runtime.py:255`.
  - Fix: Wrap in `asyncio.to_thread()` when caller is async OR replace with `await asyncio.sleep()`. Audit caller chain first.

---

## LOW (nice to have)

- [ ] **Test file size: `test_managed_agents.py` (1,333 lines)** | Pass 1 | Effort: L
  - Carry-over from 2026-04-16.
  - Fix: Split by feature.

- [ ] **Frontend dep audit** | Pass 5 | Effort: S
  - React 18.3.1, react-router 7.13.1, Vite 6.4.2, @xyflow/react 12.10.1 — all current. Quarterly review sufficient.

- [ ] **Backend dep audit** | Pass 5 | Effort: S
  - `twilio` correctly removed per 2026-04-16 fix (SDK unused; `backend/services/twilio_service.py` uses raw httpx). Anthropic at `>=0.95.0,<1`, Supabase 2.28.3, FastAPI >=0.115.6, Stripe >=11 — all current.

- [ ] **Layer violations (Pass 2) — 27 cross-imports in routers** | Pass 2 | Effort: N/A (expected)
  - `grep from backend.routers backend/routers` returns 27 hits. All but 2 are `from backend.routers.auth import _get_current_tenant / require_role` — this IS the dependency-injection seam pattern; FastAPI routers sharing auth helpers is correct.
  - The 2 non-auth cross-refs:
    - `backend/routers/calls.py:31` imports `verify_twilio_request` from `automations.py`.
    - `backend/routers/stripe_webhooks.py:16` imports from `billing.py`, and `billing.py:136` does a lazy import back → two-way coupling.
  - Fix (if addressed): extract `verify_twilio_request` to `backend/services/twilio_service.py`; break stripe↔billing cycle by extracting the shared billing primitives to `backend/services/billing_service.py`.

- [ ] **Migration 005/007 duplicate numbering** already listed in HIGH. Repeat here as doc-log item only — add note to `docs/dev-knowledge/schema-log.md`.

---

## Stats

| Metric | Count |
|--------|-------|
| Files ≥600 lines | 48 (backend + frontend; 19 in prior audit — jump mostly from frontend pages hitting threshold) |
| Files ≥1,000 lines | 27 |
| Files ≥2,000 lines | 4 (SettingsPage, widget JS × 2, ConversationsPage) |
| Layer violations (true) | 2 (calls→automations, stripe↔billing) |
| Dead code candidates | 0 flagged (heuristic noise — skipped per skill) |
| Schema drift risks (backend) | 0 (no `tenant_id`/`lead_stage`/`service_interest` on leads/conversations) |
| Schema cross-check (live DB) | DEFERRED — Supabase MCP unauthorized this session |
| `from __future__ import annotations` in backend | 0 |
| Widget byte-identical check | PASS (exit=0) |
| N+1 candidates | 0 new (prior 2 fixed 2026-04-16) |
| Sync-in-async candidates | 5 lines across `managed_agents.py` + `llm_runtime.py` — needs caller audit |
| CVEs (C/H/M) | 0/0/0 (no `npm audit` / `pip-audit` run this session) |
| Duplicate migration numbers | 2 (005, 007) — historical, documented |

---

## Progress vs 2026-04-16

| Prior item | Status 2026-04-18 |
|---|---|
| `automation_engine.py` god class (4,418 LOC) | FIXED — split into `backend/services/automation/` package (rule_engine 875, scheduled_jobs_ext 792, orchestrator 18KB, trigger, templates, scheduled/*) |
| `analytics.py` (2,023 LOC) | FIXED — now `backend/routers/analytics/` package (dashboard 628, control_center 606, operations, insights, recovery, _common) |
| `auth.py` (1,918 LOC) | PARTIAL — 1,416 now (branding → `branding_service.py` 609 LOC). Still HIGH. |
| Widget dupe | HOLDING — byte-identical verified |
| `widget_helpers.py` (1,632) | REGRESSED slightly — 1,635 now |
| Anthropic SDK pin | HOLDING — `>=0.95.0,<1` |
| Twilio SDK removal | HOLDING — no SDK imports |
| Service→router import violations | CLOSED — auth_service, campaign_service, branding_service in place |
| N+1 in `process_pending_steps` + `check_no_response_leads` | HOLDING — fixed |

New concerns this week: 4 frontend pages ≥1,600 LOC (SettingsPage, ConversationsPage, LeadDetailDrawer, EmailSequencesPage), `scheduled_jobs_ext.py` naming inversion, duplicate migration number enforcement.

---

## Recommended execution order

1. **This sprint**: `SettingsPage.jsx` split (HIGH, L) — user-facing blast radius, touched often.
2. **This sprint**: `widget_helpers.py` split (HIGH, M) — still blocking widget iteration per prior audit; regressing.
3. **Next sprint**: `ConversationsPage.jsx` + `LeadDetailDrawer.jsx` splits (HIGH, L+M).
4. **Next sprint**: `auth.py` final split — tenant_bootstrap + oauth + password_reset.
5. **Backlog**: `scheduled_jobs_ext.py` rename; `schemas.py` domain split; `main.py` router_registry extraction.
6. **Blocker**: restore Supabase MCP access for Pass 4 live-schema cross-check.

Do NOT fix in this session (`improve-architecture` skill rule — audit and fix never in same session). Hand items to `compound-engineering` with explicit split plans.

---

## Cross-refs
- `.claude/rules/user-rules.md` Rule 9 — god class threshold
- `.claude/rules/schema-discipline.md` — forbidden columns
- `audits/audit-architecture-2026-04-16.md` — prior audit
- `docs/dev-knowledge/schema-log.md` — migration history
- `docs/dev-knowledge/architecture-decisions.md` — ADR re `lead_stage_change` event name (do not rename)

Verified: all 6 passes executed; file sizes (`wc -l`), widget diff (exit=0), schema-name grep (no hits), `from __future__` grep (no hits), migration listing (108 files, duplicates at 005/007), service→router grep (2 true violations + 25 expected auth helpers), sync-in-async grep (5 lines in managed_agents/llm_runtime). Pass 4 live-schema cross-check DEFERRED (Supabase MCP 401). — PASS (partial; one deferred).
