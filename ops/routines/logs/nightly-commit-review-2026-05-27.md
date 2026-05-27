# Nightly Commit Review — 2026-05-27

**Run start:** 2026-05-27 UTC  
**Commits reviewed:** 4  
**Production code changes:** 0  
**Auto-fixes applied:** 0  
**Issues created:** 0 (GH #181 already open; carry-forward issues already tracked)

---

## Commits Reviewed

| SHA | Title | Risk | Reason |
|-----|-------|------|--------|
| `20b79ba` | subconscious: run 2026-05-26-pm (run 35) — Invoke /god-class-splitter on email_sequences.py | LOW | subconscious planning files only (7 .md + .json under `subconscious/`) |
| `ecfb8f1` | ops: morning-digest 2026-05-26 | LOW | single log file under `ops/routines/logs/` |
| `aea5fff` | subconscious: run 2026-05-26 (run 34) — Fix GH #181 AMOUNT_TO_PLAN governance mandate | LOW | subconscious planning files only (7 .md + .json under `subconscious/`) |
| `e848b87` | ops: nightly-commit-review 2026-05-26 | LOW | `.claude/skills/god-class-splitter/SKILL.md` (new), `improve-architecture SKILL.md` (1-line ref update), log file |

**No Python, JS, JSX, TS, or SQL files modified.** All changes are docs, skills, and ops logs.

---

## Production Code State Checks

### GH #181 — billing.py AMOUNT_TO_PLAN (CONFIRMED STILL OPEN, 5th consecutive review)

**File:** `backend/routers/billing.py:263–281`  
**Issue:** Current plan prices missing from `AMOUNT_TO_PLAN`:
- `15000` → `"autopilot"` ($150/mo) — **ABSENT**
- `25000` → `"professional"` ($250/mo) — **ABSENT**

**Test state:** `backend/tests/test_billing_amount_to_plan.py` still contains:
- `test_no_wrong_15000_mapping` — asserts `15000 not in AMOUNT_TO_PLAN` (backwards — should assert it IS present)
- `test_no_wrong_25000_mapping` — asserts `25000 not in AMOUNT_TO_PLAN` (backwards)
- `test_all_four_current_tiers_present` — checks `{24900, 29900, 49900, 89900}` (stale, should be `{9900, 15000, 25000, 89900}`)

**Impact:** Stripe webhook events for current autopilot/professional customers without `metadata.plan` set resolve to `None` → silent downgrade to `free`. Customers with `metadata.plan` set are unaffected.  
**Risk:** MEDIUM — billing/payments. Human approval required.  
**Action:** None today. GH #181 already open with full fix sketch.  
**Governance note:** Subconscious run 35 escalated to "critical_standing_action + mechanism_change_required" after 5 consecutive recommendations with no implementation. Recommendation loop exhausted per governance rules.

### email_sequences.py — god-class confirmed (run 35 winner)

`backend/routers/email_sequences.py`: **1255L** (confirmed `wc -l`). Exceeds 600L threshold by 2x. Three independent concerns: CRUD, enrollment, processor.

**Subconscious run 35 recommendation:** Split into `email_crud.py`, `email_enrollment.py`, `email_processor.py` under `backend/services/email_sequences/` using `.claude/skills/god-class-splitter/SKILL.md`. Estimated ~2h interactive session.  
**Pre-requisite:** Fix GH #181 first (~15 min) to avoid carrying the billing gap into a new module structure.  
**Risk:** MEDIUM — refactor with 1255L blast radius. Requires human-led session.

### PR #182 — invoices.py god-class split (Draft, 3 days open)

Still open. Subconscious backlog flags: verify against god-class-splitter 12-step checklist before merge (Steps 6, 9, 10, 11 specifically — stale importers, pytest count unchanged, no stale module refs, smoke tests present).

---

## Parking Lot Items — Status

| Item | Status | Notes |
|------|--------|-------|
| billing-constant-guard Check 11 (pre-commit) | BLOCKED | Depends on GH #181 fix first — would guard broken state if added now |
| email_sequences N+1 fixes (GH #112, #113) | BLOCKED | Best after god-class split |
| check_project_invariants.py → pre-commit Check 10 | PENDING | Sprint Item A, ~5 min |
| scripts/check-widget-sync.sh → pre-push | PENDING | Sprint Item B, ~15 min |
| .github/workflows/lead-qualifier-eval.yml | PENDING | Sprint Item D, ~20 min (GH #110) |
| Dependabot PRs #11–15 (actions bumps) | CLOSED | Not visible in open PRs — likely merged |
| Zapier plan_status enforcement (GH #107) | PENDING | MEDIUM, security |
| AI-to-Human Handoff v1 | PENDING | M effort, GH moratorium item |

---

## Open Issues Carry-Forward

| Issue | Title | Risk | Age |
|-------|-------|------|-----|
| #181 | billing: AMOUNT_TO_PLAN missing autopilot/professional current prices | MEDIUM | 4 days |
| #169 | Moratorium active: 5 pending items | — | 11 days |
| #113 | refactor: deduplicate process_sequences / run_sequence_processor | MEDIUM | 25 days |
| #112 | perf: N+1 queries in email_sequences list_enrollments and list_sequences | MEDIUM | 25 days |
| #110 | ops: wire lead-qualifier golden eval harness to CI | MEDIUM | 26 days |
| #107 | fix(zapier): enforce plan_status check in _get_api_key_client | MEDIUM | 27 days |
| #99 | bug(stripe): SignatureVerificationError catch anti-pattern | MEDIUM | 30 days |
| #98 | perf(twilio): _find_tenant_by_phone full table scan O(N) | MEDIUM | 30 days |
| #97 | bug(rate-limit): _chat_rate_limit swallows exceptions silently | MEDIUM | 30 days |
| #94 | bug(billing): IndexError in guard_checkout_for_fraud on empty charges.data | MEDIUM | 31 days |
| #93 | bug(billing): guard_checkout_for_fraud flags no_payment_required as fraud | HIGH | 31 days |

---

## Summary

Zero production code changes in the 24h window. All commits are planning/ops/docs. No bugs introduced; no regressions detectable.

Primary standing action remains GH #181 (billing gap, MEDIUM, human approval required). Secondary action is email_sequences.py god-class split (run 35 winner, ~2h, human session required).

Verified: git log --since="24 hours ago" scanned 4 commits, 0 production code files — PASS
