# Nightly Commit Review — 2026-07-16

**Run:** automated nightly-commit-review  
**Range:** last 24 hours (since 2026-07-15 ~06:00 UTC)  
**Commits reviewed:** 26  
**Issues found:** 1 MEDIUM filed (#454), 2 deferred noted  
**Fixes auto-applied:** 0 (no LOW-risk bugs found)

---

## Summary

Heavy commit day (26 commits) completing the booking notification lifecycle,
adding Agent OS quality-of-life improvements, and landing two critical
infrastructure commits (RLS lockdown + FK index migration). Code quality
is high: every feature commit carries matching tests, no schema discipline
violations, no `from __future__ import annotations` in FastAPI files.

The lone actionable finding: post-appointment automations (review requests,
rebook prompts, aftercare) still never fire automatically because appointments
stay `confirmed` forever — no job auto-completes past-confirmed slots. Filed
as #454 with a full implementation proposal.

---

## Commit Triage

### HIGH (2 commits — already applied to prod, no further action)

| SHA | Description | Risk | Status |
|-----|-------------|------|--------|
| `5b33967` | security(rls)+perf: prod RLS lockdown (#436) | HIGH-SECURITY | Resolved — applied to prod |
| `112889a` | perf(db)+demo: FK covering indexes + migration 174 (#437) | HIGH-SCHEMA | Resolved — applied to prod |

**`5b33967` detail:** Dropped `conversations_anon_access` (full cross-tenant R/W
via anon key via PostgREST), retargeted 18 always-true PUBLIC policies to
`service_role` only (previously any anon caller could read `clients`, `leads`,
`documents`, OAuth tokens, etc.), revoked EXECUTE on 8 `SECURITY DEFINER`
functions from anon/authenticated (AI-token budget, automation locks, email
quota, `rls_auto_enable`). This was a genuine vulnerability — 0 PUBLIC/anon
always-true policies remain post-apply.

**`112889a` detail:** Idempotent self-detecting DO loop covering 47 unindexed
public FKs + drops 10 duplicate indexes. Demo tenant `business_slug` NULL
causing 404 on booking pages also fixed here.

### MEDIUM (14 commits — features and bug fixes with good tests)

| SHA | Description | Notes |
|-----|-------------|-------|
| `d73072a` | perf(kb+os): threadpool offloads + widget_guard LRU + schema-log gate (#435) | LRU-bounded `_SESSION_TURN_COUNTS` (subconscious run 94 winner); threadpool offloads for KB/OS blocking I/O |
| `f143de5` | fix(appointments): reminders/automations dead — status filter wrong (#441) | Critical fix: `send_appointment_reminders` filtered on `'booked'` (never exists), now `['confirmed','booked']`; rule_engine `appointment_created` trigger same fix |
| `fc9b36f` | feat(booking): owner alert on new appointment (#440) | New `booking_alerts.py` service; best-effort, demo-safe, dedup-keyed |
| `9a48ef3` | fix(booking): reschedule re-arms reminders + cancel notifies owner (#442) | Nulls `reminder_*_sent_at` on reschedule; dedup keys namespaced (`:booked` vs `:cancelled`) |
| `0907c35` | feat(booking): notify customer when staff reschedule/cancel (#444) | New `appointment_customer_notify.py`; correctly uses `tenant_id` (not `client_id`) for appointments per schema-discipline |
| `f45b05b` | feat(booking): voice/phone bookings alert owner too (#443) | Wires `booking_alerts` into voice booking path |
| `6cc3419` | fix(widget): inject real booking URL into AI prompt (#439) | Root-cause fix for 0 bookings (21 leads / 0 appts on MTOptions, 8 leads / 0 appts on 914 Exterior). Booking URL was never injected; AI was told to share a link it never had. New `booking_prompt.py` module (Rule 9/12 compliance) |
| `39da1f3` | fix(metrics): exclude internal tenants from daily-business-digest (#438) | LOW-ish, filed under MEDIUM given metrics correctness impact |
| `ae082b0` | feat(agent-os): map hours, website, state into agent prompts (#446) | Clean prompt augmentation |
| `561e87f` | fix(agent-os): per-agent auto-send toggle actually works (#447) | Toggle was wired to wrong state key; frontend + backend fix |
| `fc33c05` | feat(agent-os): real send outcome + retry on approved deliverables (#448) | Polls `os_action_runs` for true send result; surfaces failure + retry button |
| `f693c0b` | feat(agent-os): one-click routing clarify picker (#449) | `clarify_between` + `decision_id` threaded to UI; one-click re-route via `force_agent_id` |
| `97a6512` | fix(agent-os): auto-send config correctness (#450) | Removes dead pre-refactor skill IDs from `NEVER_AUTO_SEND_AGENTS`; restores `lead_nurture` + `review_requester` (missed-call text-backs, review requests) to `AUTO_SEND_AGENTS` |
| `07315f6` | feat(leads): owner alert on public-form + Messenger lead capture (#445) | Fires `fire_new_lead_alert_background` on first-contact Messenger and public form submit; dedup guard on new leads only |

### LOW (10 commits — docs, ops logs, automated entries)

| SHA | Description |
|-----|-------------|
| `fe4253b` | docs: auto-log bug fix from 97a6512 |
| `465c531` | docs: auto-log bug fix from 561e87f |
| `998c0f4` | docs: auto-log bug fix from f45b05b |
| `8ca16e6` | docs: auto-log bug fix from 9a48ef3 |
| `e3f9e81` | docs: auto-log bug fix from f143de5 |
| `b3ee0fd` | docs: auto-log bug fix from 6cc3419 |
| `a9cbd26` | docs: auto-log bug fix from 39da1f3 |
| `c7a0e07` | ops: morning-digest 2026-07-15 |
| `922f7ac` | subconscious: run 2026-07-15 — LRU bound fix |
| `9ea9b3f` | ops: nightly-commit-review 2026-07-15 |

---

## Issues Filed This Run

| # | Title | Risk |
|---|-------|------|
| #454 | feat(booking): auto-complete past-confirmed appointments so review/aftercare automations fire | MEDIUM |

---

## Deferred Items (not filed, noted for context)

**Supabase RLS advisor backlog (from migration 173):** 64 `auth_rls_initplan`
warnings, 216 `multiple_permissive_policies` cases, 83 `unused_index` entries.
All deferred because all prod traffic is `service_role`/`BYPASSRLS` (0 real
cost). Revisit if direct-auth traffic is ever introduced.

**Issue #399 still open:** `AUTOPILOT_GH_TOKEN` expired — autopilot-issue-loop
has been dead since 2026-07-04. 30 open `ai-ready` issues await. No related
commits in this review window; still needs human token rotation.

---

## Schema Discipline Check

- No `tenant_id` used on `leads`/`conversations` tables in new code (correct: `client_id`)
- No `lead_stage` column references (correct: `status`)
- No `service_interest` column references (correct: `areas_of_interest`)
- No `from __future__ import annotations` in any new FastAPI service files
- `appointment_customer_notify.py` explicitly documents `tenant_id` for appointments (correct per schema)

All invariants: **PASS**

---

## Verified

No LOW-risk auto-fixable bugs identified. All fixes in this window were shipped
with proper tests. Next action: owner review of #454 (booking auto-complete gap)
and #399 (token rotation for autopilot loop).
