# Architecture Audit — 2026-04-29

**Tool:** `.claude/skills/improve-architecture/scripts/audit.py` + targeted greps.
**Scope:** Repo state at commit `f54dc7e` (attribution slice 1).
**Total issues:** 57 (12 CRITICAL, 22 HIGH, 23 MEDIUM, 0 LOW).
**Rule:** This file is a report. No fixes in this session — see `daily-skills.md` "don't fix and audit in same session".

---

## CRITICAL — fix in next architecture window

### God classes (>1000 lines) — Rule 9 violation

| File | LOC | Notes |
|------|-----|-------|
| `widget/agentnexlify-widget.js` | 2048 | Widget JS — byte-identical pair with `frontend/public/widget/`. Splitting requires extra care to keep both copies in sync. |
| `backend/routers/auth.py` | 1506 | High-risk surface. Auth + JWT + OAuth + password reset likely all here. Top split candidate. |
| `backend/tests/test_managed_agents.py` | 1374 | Test file — split by agent (lead-qualifier, document-drafter, codebase-reviewer). |
| `backend/routers/widget_chat.py` | 1271 | Widget chat router — likely split into stream/non-stream + helpers. |
| `backend/routers/invoices.py` | 1211 | Routes + PDF gen + Stripe. Split into module. |
| `backend/routers/onboarding.py` | 1199 | Multi-step onboarding flow. Split by step. |
| `backend/routers/calls.py` | 1175 | Twilio routes + missed-call logic. Split by intent. |
| `backend/routers/leads.py` | 1158 | Lead CRUD + bulk + export. Split by op. |
| `backend/routers/email_sequences.py` | 1065 | Sequences CRUD + trigger logic. |
| `backend/routers/booking_page.py` | 1065 | Public booking + admin booking. Split. |

**Effort estimate:** L (1-2 days each), most M after pattern established. Auth is the highest-risk split — do it first with `parallel-approaches` rule + `/ultrareview`.

### Layer violations (router referencing frontend concepts)

| Path | Detail |
|------|--------|
| `backend/routers/conversation_inbox.py:217` | Comment-only ref ("session_id from frontend") — false positive but worth confirming code is clean. |
| `backend/routers/conversation_inbox.py:244` | Same pattern. |

**Effort:** S — comment cleanup only.

---

## HIGH — schedule within 2 weeks

### God classes (600-1000 lines)

22 files. Pattern:

- **Routers (15):** `billing.py`, `bids.py`, `client_portal.py`, `channels_facebook.py`, `widget_lead_helpers.py`, `marketing_campaigns.py`, `appointments.py`, `social_media.py`, `sequences.py`, `forms.py`, `pipeline.py`, `admin_analytics.py`, `widget_chat_helpers.py`, `analytics/control_center.py`, `analytics/dashboard.py`. → router-folding pattern: extract handlers + helpers per concern.
- **Services (4):** `local_seo_handlers.py` (886), `branding_service.py` (606), `booking.py` (622), `automation/rule_engine.py` (875), `automation/scheduled_jobs_ext.py` (792). → split by use-case (e.g. branding fonts vs colors vs assets).
- **Core (2):** `backend/main.py` (909), `backend/models/schemas.py` (999). → main.py routes section already well over Rule 9; schemas.py needs split by domain (auth/leads/widget/billing).

**Effort:** M each, L for `main.py` and `schemas.py` (high-cardinality imports).

---

## MEDIUM — sweep this week

### Dead imports (23 found)

Quick win — single PR, regex grep + delete. Top hot spots:

- `backend/services/automation/scheduled_jobs/_common.py` — **8 dead imports** in one file. Indicates this module was refactored and never cleaned up.
- `backend/routers/conversations.py:7-8` — `get_current_tenant`, `branding_service` unused.
- `backend/routers/faq.py:8-9` — same pair unused.
- `backend/routers/auth.py:330` — `INDUSTRY_FAQS` unused.
- Misc one-off imports in `main.py`, `widget_chat.py`, `appointments.py`, `widget_config.py`, `integrations.py`, `branding_service.py`, `automation_engine.py`, `rule_engine.py`, `analytics/__init__.py`.

**Effort:** S — one PR, ~10 min.

---

## LOW — none

Audit script found no LOW-severity issues this run.

---

## Counter-signals (healthy areas)

- **Schema drift:** 117 migrations applied, sequential, no gaps. Latest `117_zapier_api_keys.sql`.
- **Test coverage breadth:** 27 test files in `backend/tests/`. New `test_activity.py` (just added) wires attribution properly.
- **TODO/FIXME density:** 1 in entire `backend/` Python tree — exceptionally low debt markers.
- **Frontend god classes:** none detected (frontend not surveyed by current script — possible blind spot).
- **Dependency rot:** not surveyed this pass — see "Gaps" below.

---

## Gaps in this audit (skill scope did not cover)

1. **Frontend** — `frontend/src/**/*.jsx` not scanned for god classes. Likely candidates: `Dashboard.jsx`, `ActivityPage.jsx` (new), `Settings.jsx`.
2. **Dependency rot** — no `pip-audit` or `npm audit` run.
3. **Performance hotspots** — no profiling/N+1 detection. Plans/audits should examine: chat-widget DB calls per message, lead-list pagination, sequence dispatch.
4. **RLS / tenant isolation drift** — no automated check that all routers use `tenant_select`/`tenant_table` helpers.
5. **Widget byte-identical** — assumed; not verified in this audit.

---

## Suggested next actions (do NOT execute in this session)

1. **Backlog issue:** "Split `backend/routers/auth.py` (1506 LOC) into auth/login + auth/reset + auth/oauth modules" — CRITICAL, auth surface, requires `/ultrareview`.
2. **Quick PR:** "Remove 23 dead imports across backend" — MEDIUM, one-shot, low risk.
3. **Backlog issue:** "Split `backend/models/schemas.py` (999 LOC) by domain" — HIGH, blast-radius across 30+ importers, needs `gitnexus_impact` first.
4. **Backlog issue:** "Audit frontend for god classes + run dependency rot pass" — gap-fill.
5. **Backlog issue:** "Investigate `automation/scheduled_jobs/_common.py` (8 dead imports) — likely deeper refactor smell."

---

## Audit metadata

- **Date:** 2026-04-29
- **Branch:** main
- **Commit:** f54dc7e
- **Audit script version:** `.claude/skills/improve-architecture/scripts/audit.py`
- **Compliance with daily-skills rule:** report-only; no fixes applied.
