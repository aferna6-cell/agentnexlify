# Subconscious Ideas — 2026-06-20 (Run 63)

## Evidence Summary

Nightly 2026-06-20 confirms: **zero code commits in last 24h** (5 ops/planning artifacts only). Both
revenue bugs remain open for 4 days each.

- **GH #308** (HIGH): Stripe webhook idempotency early-write — day 4, 5th consecutive flagging cycle.
  `idempotency.py:85-93` writes row BEFORE handler runs; handler failure → Stripe retry skips →
  payment event permanently dropped → tenant stuck dunning-locked after card fix.
- **GH #292/#293** (MEDIUM): chatbot/agent_os missing from 3 plan-name dicts — day 4.
  Every new paid signup since 2026-06-16 gets wrong SMS limits and Zapier 402.
- **RUN 63 MANDATE fires**: GH #292/#293 unimplemented → switch winner back to GH #308
  (per run 62 winning-concept.md §RUN 63 MANDATE).
- KB stale 46 days (last compiled 2026-05-05). kb-autopopulate.sh broken since June.
- check_project_invariants.py passes all 6 checks. Leadgen pipeline shipping (OSM/merge/enrich).
- Home.jsx 1006L, email_sequences.py 1143L — god-class candidates parked.

---

## Idea 1: Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events [RUN 63 MANDATE]

**Evidence:** Run 62 winning-concept.md §RUN 63 MANDATE: "if GH #292/#293 still unimplemented →
winner switches to GH #308 (full sketch exists, ~20 min)." Nightly 2026-06-20 confirms GH #292/#293
unimplemented — mandate fires. GH #308 flagged 5 consecutive cycles (runs 59/60/61/62/63).
`idempotency.py` direct read (run 60 + nightly 2026-06-20): no `delete_key` method exists.
Handler throws → idempotency row persists → Stripe retry short-circuits → event dropped.

**Action:** Add `async def delete_key(supabase, key)` to `backend/services/idempotency.py`.
Call `await delete_key(db, idempotency_key)` in `stripe_webhooks.py` exception handler before
re-raising `HTTPException(500)`. Write regression test: FAILS on HEAD (row persists on exception),
PASSES after fix.

**Impact:** Stops permanent payment event drops. Tenants who fix their card can re-enter billing
cycle. Payment recovery dunning unlock restored.

**Category:** code_health

---

## Idea 2: Fix GH #292/#293 — Wire chatbot/agent_os into Plan-Name Dicts [Carry-Over Run 62]

**Evidence:** Nightly 2026-06-20 confirms all 3 files still unpatched: sms_rate_limiter.py line 10
(_UNLIMITED_PLANS missing chatbot/agent_os), api_key_auth.py line 29 (_ALLOWED_PLANS missing both),
billing_reconciliation.py caps missing both. Every new paid signup since repricing 2026-06-16 gets
wrong SMS limits (capped at 50/day free tier) and Zapier 402.

**Action:** Add chatbot/agent_os to _UNLIMITED_PLANS (sms_rate_limiter.py), _ALLOWED_PLANS
(api_key_auth.py), and _PLAN_AGENT_RUN_CAPS/_PLAN_BASELINE_AI_TOKENS (billing_reconciliation.py)
with parity-tier defaults (confirm chatbot SMS limit with product).

**Impact:** Fixes product breakage for all new paid tenants since 2026-06-16.

**Category:** code_health

---

## Idea 3: Add Plan-Name Guard check_7 to check_project_invariants.py [AUTONOMOUS-EXECUTABLE]

**Evidence:** check_project_invariants.py passes all 6 checks and has autonomous precedent (checks
10/11/12/13 all landed autonomously). The structural gap: billing repricing 2026-06-16 didn't
propagate to 3 service files — same pattern as AMOUNT_TO_PLAN drift in old billing.py.
A check 7 scanning for chatbot/agent_os in those 3 files would have caught this at commit time.

**Action:** Add check 7 to `scripts/check_project_invariants.py`: grep sms_rate_limiter.py,
api_key_auth.py, billing_reconciliation.py for "chatbot" and "agent_os". FAIL if absent. ~15 lines
Python. AUTONOMOUS-EXECUTABLE by nightly review.

**Impact:** Prevents future plan-name drift at commit. Self-healing loop after GH #292/#293 is fixed.

**Category:** code_health / operational

**SEQUENCING NOTE:** Blocked until GH #292/#293 is fixed — adding check 7 now would FAIL every
commit. Recommend as Bonus B after GH #292/#293 fix.

---

## Idea 4: Investigate GH #263 — 24 Pending Migrations (CRITICAL, 5+ days)

**Evidence:** GH #263 added to parking_lot in run 62 (ROI 2.3) — "CRITICAL flag, 5 days."
Governance note: "Triage first before proposing fix — could be applied-but-not-tracked vs
genuinely pending." Leadgen pipeline just shipped 3 new features (OSM/merge/enrich) with potential
migration requirements. KB doesn't track migration status automatically.

**Action:** Triage GH #263: query Supabase for applied migrations (`select name from
schema_migrations order by executed_at desc limit 30`), diff against `migrations/` directory.
If genuinely pending: create migration-apply runbook. If stale tracker: close issue + add guard.

**Impact:** Eliminates schema drift risk. 24 genuinely pending migrations is a production data
integrity risk for all tenants.

**Category:** operational

---

## Idea 5: Fix kb-autopopulate.sh (46 days stale, agent-browser CLI missing)

**Evidence:** KB INDEX.md shows last compiled 2026-05-05 (46 days ago). kb-autopopulate.sh noted
broken in runs 53-54 (parking_lot ROI 1.8, agent-browser CLI not installed). KB-first rule
(CLAUDE.md, `.claude/rules/kb-first.md`) has zero benefit when KB is 46 days stale. Competitive
intelligence missing: Intercom Fin Apex vertical models, GHL Field Service, GHL Unlimited AI
$97/sub breakdown — all uncompiled. Leadgen pipeline shipping without competitive context.

**Action:** Diagnose `scripts/daily/kb-autopopulate.sh`: identify agent-browser dependency, replace
with curl/WebFetch calls or add silent fallback when unavailable. Trigger manual KB compile.

**Impact:** Restores twice-daily KB auto-population. KB-first rule becomes usable again.
Competitive intelligence compounding resumes.

**Category:** operational / workflow
