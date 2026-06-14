# Architecture Audit — 2026-06-10

Lean pass (the delegated audit agent died at its token cap; this is the
parent-session replacement). Six passes; ranked fix list. Fixes belong in a
follow-up session except where marked done.

## CRITICAL

**C1. Stage migration 137 to drop `tenants.marketing_addon_*` — ONLY after the removal code deploys.**
The add-on was removed 2026-06-10; four columns (`marketing_addon_active/_grandfathered/_started_at/_stripe_sub_id`) become unread once the removal merges. ORDERING MATTERS: the currently-deployed backend still SELECTs `marketing_addon_active` in `/me` — dropping the columns before the rollout 500s every authenticated user. Staged as `migrations/137_drop_marketing_addon_columns.sql` (marked DO-NOT-APPLY-YET); apply only after Railway runs the removal commit. Severity: CRITICAL if mis-ordered, trivial if sequenced. Effort: S.

## HIGH

**H1. `backend/routers/auth.py` — 1,598 lines, five concerns.** Register/login/JWT + Google OAuth + password reset + billing checkout/cancel + dashboard/widget-config passthroughs. Auth is the worst place for a god file. Split: `auth_google.py`, `auth_password_reset.py`, `auth_billing.py` (router-level, keep `/api/v1/auth` prefix); use god-class-splitter + post-split-test-repair skills. Effort: L (15+ test files patch `backend.routers.auth.*` targets).

**H2. Dead frontend pages (56 files in pages/).** `ContentStudioPage.jsx` has ZERO imports anywhere (not even App.jsx) — delete now. The 10 newly-hidden pages (marketing set + calendar/invoices/documents) are one-ref (route map only) — keep routable per the prune pattern, but `ABTestsPage.jsx` (1,119 lines) is nav-hidden, plan-gated, and duplicates the platform pricing experiment conceptually — candidate for deletion next session after checking tenant usage (`ab_tests` table row count). Effort: S each.

**H3. Schema drift beyond the hot tables.** Migrations 001–010 claim columns for tables outside the drift guard's 7 (e.g. `documents`, `bids`, `email_events`). The referral incident proves the failure class. Extend `hot_table_columns()` + manifest to every table the backend WRITES (grep `.insert(`/`.update(` targets) — ~15 more tables. Effort: M.

## MEDIUM

**M1. Frontend page bloat:** LocalSEOPage 2,253 / ConversationsPage 2,039 / IntegrationsPage 1,828 / LeadDetailDrawer 1,688. None blocking; split when next touched (Rule 9).

**M2. Router-imports-router:** `stripe_webhooks.py` imports 6 handlers from `billing.py`. Move shared webhook handlers to `backend/services/stripe_webhook_handlers.py`; both routers import the service. Effort: M (test patch targets move).

**M3. `backend/routers/email_sequences.py` 1,255 + `invoices.py` 1,211 + `onboarding.py` 1,199** — same Rule 9 treatment when next touched.

## LOW

**L1.** `widget_chat.py` 1,299 — hot path, working, heavily tested; split only with strong cause.
**L2.** ~~Retired plan-name sidebar entries~~ — already removed by a prior commit (verified absent 2026-06-11).
**L3.** `tests/` vs `backend/tests/` cross-contamination: combining both suites in ONE pytest process fails 2 widget tests (pre-existing, verified on pre-change tree). CI runs them separately; document or isolate fixtures. Effort: M.

## Verified non-issues
- No `from __future__ import annotations` in backend (pre-commit enforces).
- Routers register cleanly (app import smoke passes; 611 backend tests).
- No direct Postgres deps (PostgREST-only confirmed in pool audit).

## Next-session order
1. C1 (apply 137 after this PR deploys — 5 min)
2. H2 ContentStudioPage deletion + ABTestsPage usage check
3. H3 drift-guard expansion
4. H1 auth.py split (own session, god-class-splitter)
5. M2 webhook handler extraction

---

## Addendum — delegated deep-audit findings (agent returned after the lean pass above)

### CRITICAL (new)
- **Migration 001 stale DDL**: declares `leads.tenant_id` / `service_interest` / `lead_stage` and `conversations.tenant_id`; live uses `client_id` / `areas_of_interest` / `status`. NO migration ever creates `leads.status` or `leads.areas_of_interest` — they exist ad-hoc in prod only. Fresh-DB replay does not reproduce production. Fix: documenting reconciliation migration (next session; pairs with drift-guard expansion H3).
- **Duplicate migration numbers**: 005 ×2, 007 ×3 (historical — document canonical order, never renumber applied files). 135 ×2 was created TODAY — redundant `135_backfill_referral_codes.sql` deleted (never applied; `135_referral_columns.sql` covers it).

### HIGH (new)
- `lead_scoring.score_all_leads` (backend/services/lead_scoring.py:286): 3 queries per lead in a loop, unbounded — batch-fetch + score in memory.
- `onboarding.py:485` per-FAQ insert loop — **FIXED this session** (batched like the wizard-FAQ insert below it).

### MEDIUM (new)
- `@xyflow/react` dep with zero imports (orphaned by Chat Flows prune) — **REMOVED this session**.
- Bulk-send N+1s: `invoices.py:1145-1198` (capped at 50), `leads.py:714,866` CSV import writes — batch when next touched.
- `time.sleep` in retry loops: `llm_runtime.py:316`, `managed_agents.py` (async route already offloads via threadpool — verify llm_runtime callers only).
- ~~`chat_flows.py` router removal~~ — WRONG premise (verified 2026-06-11): `widget_chat.py:829` and `dashboard_service.py:223` READ chat_flows; MTOptions has live rows. Router stays.

### Corrections to the lean pass
- ABTestsPage IS reachable (App.jsx import, plan-gated) — usage check still warranted before deletion.
- `stripe_webhooks` ← `billing` import is documented-intentional; downgraded to LOW (extract to services/ opportunistically).
