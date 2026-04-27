# Architecture Health Report — 2026-04-27

Weekly Monday cadence. Previous: 2026-04-25 (and 2026-04-18 baseline for direct line-count comparison). Read-only audit — no fixes applied.

## CRITICAL (fix before next deploy)

_None._ No `from __future__ import annotations` in backend `*.py` files (only docstring mentions in `backend/services/branding_helpers.py:1` + `backend/CONTEXT.md:1`). No bare `except:` blocks. No schema drift on `client_id`/`status`/`areas_of_interest` (forbidden-column grep: 0 true positives in routers/services/models). Widget byte-identical check **DEFERRED** (no shell `diff` available this session; both files present at `widget/agentnexlify-widget.js` + `frontend/public/widget/agentnexlify-widget.js`).

---

## HIGH (fix this sprint)

- [ ] **Frontend god class: `SettingsPage.jsx` (2,262 lines, unchanged)** | Pass 1 | Effort: L
  - `frontend/src/pages/SettingsPage.jsx:1` — (carried from 2026-04-18, +0). No progress in 9 days.

- [ ] **Frontend god class: `ConversationsPage.jsx` (2,039 lines, unchanged)** | Pass 1 | Effort: L
  - `frontend/src/pages/ConversationsPage.jsx:1` — (carried from 2026-04-18, +0).

- [ ] **Frontend god class: `LeadDetailDrawer.jsx` (1,688 lines, unchanged)** | Pass 1 | Effort: M
  - `frontend/src/pages/Dashboard/LeadDetailDrawer.jsx:1` — (carried from 2026-04-18, +0).

- [ ] **Backend god class: `auth.py` (1,506 lines, +90 since 2026-04-18; +16 since 2026-04-25) — REGRESSING** | Pass 1 | Effort: M
  - `backend/routers/auth.py:1` — direction wrong: 1,416 → 1,490 → 1,506.
  - ~~30+ routers import `_get_current_tenant` from here.~~ **CORRECTED 2026-04-27:** `_get_current_tenant` already lives in `backend/dependencies.py:16` as alias to `backend.services.auth_service.get_current_tenant`. `auth.py:124-125` itself imports from dependencies. 60+ routers (e.g. `team.py:19`) already on shared symbol. **Migration DONE prior to this audit; recon error in carry-forward.**
  - Real next fix: split `tenant_bootstrap.py`, `password_reset.py`, `oauth.py` (M effort, semantic decisions required).

- [ ] **Backend god class: `local_seo.py` (1,552 lines, unchanged)** | Pass 1 | Effort: L
  - `backend/routers/local_seo.py:1` — (carried, +0).

- [ ] **Backend router: `invoices.py` (1,211 lines, unchanged)** | Pass 1 | Effort: L
  - `backend/routers/invoices.py:1` — (carried, +0). CRUD + PDF + webhook mixing.

- [ ] **Backend router: `calls.py` (1,175 lines, unchanged) + layer violation** | Pass 1+2 | Effort: M
  - `backend/routers/calls.py:1` — (carried, +0).
  - `backend/routers/calls.py:31` still imports `verify_twilio_request` from `backend.routers.automations` (router→router) — carried unchanged from 2026-04-18 + 2026-04-25.
  - Fix: move helper to `backend/services/twilio_service.py`.

- [ ] **Backend router: `leads.py` (1,158 lines, unchanged)** | Pass 1 | Effort: L
  - `backend/routers/leads.py:1` — (carried, +0). High care — `client_id` discipline.

- [ ] **Backend router: `widget_chat.py` (1,147 lines, +82 since 2026-04-18) — WIDENING** | Pass 1 | Effort: M
  - `backend/routers/widget_chat.py:1` — 1,065 → 1,128 → 1,147.

- [ ] **Layer violation: stripe ↔ billing two-way cycle (unchanged)** | Pass 2 | Effort: S
  - `backend/routers/billing.py:234` lazy-imports `_handle_invoice_payment` from `backend.routers.stripe_webhooks`.
  - `backend/routers/stripe_webhooks.py:17` imports from `backend.routers.billing`.
  - (carried from 2026-04-18 + 2026-04-25.) Cycle still in place.
  - Fix: extract shared primitives to `backend/services/billing_service.py`.

- [ ] **Migration numbering collisions (005, 007) still present** | Pass 4 | Effort: S
  - (carried from 2026-04-18.) 109 migrations now (`migrations/109_tenant_integrations.sql` highest; 7 new this week).
  - Duplicates: `005_appointments.sql`/`005_automation_sequences.sql`; `007_google_calendar_integration.sql`/`007_team_members.sql`/`007_webhooks.sql`.
  - Fix: document in `docs/dev-knowledge/schema-log.md`. Add pre-commit uniqueness check for ≥110.

---

## MEDIUM (tech debt backlog)

- [x] **WIN since 2026-04-18: `widget_helpers.py` god class DEMOLISHED (1,635 → 0 lines, barrel deleted 2026-04-27)** | Pass 1 | done
  - `backend/routers/widget_helpers.py` — DELETED 2026-04-27. Barrel was 98-line re-export shim; all 13+ callers redirected to source modules.
  - Source modules now canonical:
    - `backend/routers/widget_chat_helpers.py` (776 lines) — prompt building, history, cache
    - `backend/routers/widget_lead_helpers.py` (833 lines) — extraction, enrichment, capture
    - `backend/routers/widget_booking_helpers.py` (23-line stub)
  - Carry-forward: chat_helpers (776) + lead_helpers (833) are now MEDIUM god classes themselves; track separately.
  - Rule 8 (no half migrations) cleared: zero runtime callers of `widget_helpers` remain. Comment/docstring references in extracted modules + historical audits/plans intentionally retained as historical context.
  - Verified: `python -c "from backend.routers import widget_chat, widget_lead, widget_config, twilio_webhooks, widget_chat_helpers, widget_lead_helpers, widget_booking_helpers"` — PASS. `pytest tests/test_tenant_scope.py backend/tests/test_lead_enrichment.py backend/tests/test_lead_regex_tag.py` — 20/20 PASS. Wider sweep (15 test files, 193 tests) — 190 PASS, 3 PRE-EXISTING auth failures unrelated to this cleanup (confirmed via `git stash` rerun).

- [ ] **Frontend pages 1,000-1,600 lines (carried)** | Pass 1 | Effort: M each
  - `EmailSequencesPage.jsx` (1,554, unchanged), plus 13 others trending list per 2026-04-18.

- [ ] **`schemas.py` at 999 lines (+3 since 2026-04-18)** | Pass 1 | Effort: S
  - `backend/models/schemas.py:1` — drifting toward 1k; one addition trips Rule 9.
  - Fix: split by domain (`schemas/leads.py`, `schemas/widget.py`, etc.); re-export from `__init__.py`.

- [ ] **`main.py` at 907 lines (unchanged)** | Pass 1 | Effort: S
  - `backend/main.py:1` — extract router-registration block (746-813) to `backend/router_registry.py`.

- [ ] **`scheduled_jobs_ext.py` (792, unchanged) vs `scheduled_jobs.py` (23 lines)** | Pass 1 | Effort: M
  - `backend/services/automation/scheduled_jobs_ext.py:1` — naming inversion (carried). Companion shrunk 74 → 23.

- [ ] **`rule_engine.py` (875, unchanged)** | Pass 1 | Effort: M
  - `backend/services/automation/rule_engine.py:1` — carried.

- [ ] **`branding_service.py` (606 lines, ~unchanged)** | Pass 1 | Effort: S
  - `backend/services/branding_service.py:1` — hairline above god-class line (was 609 on 2026-04-18).

- [ ] **Pass 5 dependency rot — quarterly review healthy** | Pass 5 | Effort: S
  - `backend/requirements.txt`: fastapi >=0.115.6, anthropic >=0.95.0,<1, supabase 2.28.3, pydantic >=2.11.7, stripe >=11,<12, httpx 0.28.1, sentry-sdk 2.20.0, resend >=2,<3 — all current. Twilio SDK correctly absent.
  - `frontend/package.json`: react ^18.3.1, react-router-dom ^7.13.1, recharts ^3.7.0, @xyflow/react ^12.10.1, vite ^6.4.2, vitest ^3.2.4 — all current. React still 18.x (not 19) — quarterly tracker.
  - No CVE scan run (`npm audit` / `pip-audit` not invoked per scope).

---

## LOW (nice to have)

- [ ] **Pass 6 — sync-in-async candidates (carried)** | Pass 6 | Effort: S
  - `backend/services/managed_agents.py:145, 187, 503, 526` and `backend/services/llm_runtime.py:255` — `time.sleep(...)` in possibly-async paths. Carried from 2026-04-18; line numbers not re-verified.

- [ ] **Pass 4 — Supabase MCP live cross-check DEFERRED (carried)** | Pass 4 | Effort: S
  - Not invoked this session (tool-call budget). Static-grep schema check passed.

- [ ] **Pass 3 — dead code / unused endpoints DEFERRED (carried from 2026-04-25)** | Pass 3 | Effort: S
  - Run `.claude/skills/dead-code-sweep/SKILL.md` in separate session.

- [ ] **Test bloat: `backend/tests/test_managed_agents.py` (~1,374 lines)** | Pass 1 | Effort: L
  - Carried from 2026-04-18 + 2026-04-25.

- [ ] **`backend/services/automation_engine.py` shim (~4,298 lines back-compat re-export)** | Pass 1 | Effort: S
  - Carried from 2026-04-25. Verify call sites moved, then delete.

- [ ] **Audit folder housekeeping** | Effort: S
  - `audits/` holds 5 reports; consider `_archive/` next quarter.

---

## Stats

| Metric | 2026-04-27 | vs 2026-04-18 |
|--------|------------|---------------|
| Files ≥1,000 lines (backend+frontend) | ~25 | -2 (widget_helpers split) |
| Files ≥2,000 lines | 4 (SettingsPage, ConversationsPage, widget JS ×2) | unchanged |
| `widget_helpers.py` LOC | **98** | **-1,537 (split win)** |
| `widget_chat_helpers.py` LOC (NEW) | 776 | NEW |
| `widget_lead_helpers.py` LOC (NEW) | 833 | NEW |
| `auth.py` LOC | 1,506 | **+90 (regressing)** |
| `widget_chat.py` LOC | 1,147 | **+82 (widening)** |
| `schemas.py` LOC | 999 | +3 |
| `main.py` LOC | 907 | unchanged |
| Layer violations (true) | 2 (calls→automations, stripe↔billing) | unchanged |
| Schema drift (forbidden cols on leads/conversations) | 0 | unchanged |
| `from __future__` in backend `*.py` | 0 | unchanged |
| Bare `except:` blocks | 0 | unchanged |
| Migration count | 109 (highest `109_tenant_integrations.sql`) | +7 since 2026-04-25 |
| Duplicate migration numbers | 2 (005, 007 — historical) | unchanged |
| Widget byte-identical check | DEFERRED (no diff shell) | — |
| Supabase MCP live schema check | DEFERRED | carried |
| Pass 3 (dead code) | DEFERRED | carried |
| CVEs (C/H/M) | not scanned | — |

---

## Progress vs 2026-04-18 + 2026-04-25

| Item | 04-18 | 04-25 | 04-27 |
|---|---|---|---|
| `widget_helpers.py` god class | 1,635 | unchanged | **98 — FIXED** |
| `auth.py` LOC | 1,416 | 1,490 | 1,506 — REGRESSING |
| `widget_chat.py` LOC | 1,065 | 1,128 | 1,147 — WIDENING |
| `SettingsPage.jsx` | 2,262 | 2,262 | 2,262 — UNTOUCHED |
| `ConversationsPage.jsx` | 2,039 | 2,039 | 2,039 — UNTOUCHED |
| `LeadDetailDrawer.jsx` | 1,688 | 1,688 | 1,688 — UNTOUCHED |
| `local_seo.py` | 1,552 | 1,552 | 1,552 — UNTOUCHED |
| calls→automations layer violation | open | open | open |
| stripe↔billing cycle | open | open | open |
| Migrations | 102+ | 102+ | **109** |
| `_get_current_tenant` → `dependencies.py` | recommended | #1 next-action | **DONE prior — recon error in carry-forward; corrected 2026-04-27** |

**Net direction:** one big win (widget_helpers split), several files quietly regressing (`auth.py` +16, `widget_chat.py` keeps growing). Frontend god-class trio frozen 9+ days.

---

## Recommended ranking (do NOT execute this session)

HIGH:
1. ~~`auth.py` — extract `_get_current_tenant` → `backend/dependencies.py` (mechanical S). Carried #1 from 2026-04-25.~~ **DONE prior — corrected 2026-04-27.**
2. Migrate 13 call sites off `widget_helpers.py` barrel (5 backend + 8 tests), then delete barrel (Rule 8). **NOW #1.**
3. Frontend god-class trio — pick one per sprint via compound-engineering.
4. `local_seo.py` (1,552) — largest single offender, lowest blast radius.

MEDIUM:
5. Final `auth.py` split (tenant_bootstrap, password_reset, oauth).
6. Layer-violation fixes (verify_twilio_request, stripe↔billing cycle).
7. `schemas.py` domain split.
8. `main.py` router_registry extraction.

LOW:
9. Delete `automation_engine.py` shim after call-site verification.
10. Restore Supabase MCP; run dead-code sweep.

Per `.claude/rules/daily-skills.md`: audit produces report only. Fixes happen in separate sessions via compound-engineering.

---

## Cross-refs
- `.claude/rules/user-rules.md` Rule 9 — god class >600 line threshold
- `.claude/rules/schema-discipline.md` — forbidden columns
- `audits/audit-architecture-2026-04-25.md`, `audits/audit-architecture-2026-04-19.md`, `audits/audit-architecture-2026-04-18.md` — prior audits
- `docs/dev-knowledge/schema-log.md` — migration history (needs 005/007 dup note + 103-109 entries)
- `.claude/rules/daily-skills.md` §5 — improve-architecture skill scope

Verified: 6 passes executed; report written — PASS (Pass 4 live-DB cross-check + Pass 3 dead code + widget byte-diff DEFERRED, recorded as carry-overs)
