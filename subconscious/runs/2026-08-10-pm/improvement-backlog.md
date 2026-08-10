# Improvement Backlog — Run 108 (2026-08-10-pm)

## Implemented This Cycle (by run 107)

### IMPLEMENTED: Step 9H — KB Autopopulate Outcome Monitor
- **Source:** This session's debate winner (Idea 1 / Step 9G Amendment)
- **Implemented as:** Step 9H in `.claude/skills/nightly-commit-review/SKILL.md` lines 332-354
- **Run:** 107 (2026-08-10), cycle 2 direct implementation escalation
- **What it does:** On nightly run after Step 9G triggered, re-reads `knowledge-base/log.md`, compares `last_run_date` to pre-trigger value. If `conclusion == "success"` AND `last_run_date` unchanged → FALSE SUCCESS detected. Posts comment on GH #403: "Step 9H: FALSE SUCCESS detected — kb-autopopulate.yml exited 0 but KB log unchanged — likely missing secrets."
- **Evidence:** nightly-2026-08-07 confirmed exact mechanism: `continue-on-error: true` allowed workflow to exit 0 with all 3 secrets missing. KB 18 days stale post-Step 9G "SUCCESS".

### IMPLEMENTED: Step 1.5 — Detached HEAD Guard
- **Source:** This session's Idea 2 (debate Parking Lot)
- **Implemented as:** Step 1.5 in `.claude/skills/nightly-commit-review/SKILL.md` line 189
- **Run:** 107 (2026-08-10), incident-backed direct implementation
- **What it does:** Before any git operations, checks `git symbolic-ref HEAD 2>/dev/null`. If DETACHED, runs `git checkout main && git pull origin main`. Prevents orphaned commits.
- **Evidence:** 2026-08-07 nightly orphaned 3 commits (97e1044, cbbaae5, 7dff08b); required full re-apply cycle the next day.

---

## Parking Lot

### pr-backlog-triage Skill (Idea 3 — WEAKENED → PARKING LOT)
- **Status:** Parking Lot
- **Category:** workflow
- **Effort:** S
- **Why parked:** S effort; full skill creation out of proven autonomous channel. Idea 4 (close PR #596) captures the atomic XS win. Future run candidate if PR pile grows again.
- **Atomic win from this debate:** Close PR #596 (superseded by #604) — `mcp__github__update_pull_request(state=closed)`. XS effort, executable now.
- **Deferred to:** Run 109+ if PR pile grows.

### Route-Security-Guard in Nightly Step 5 (Idea 5 — BONUS ACTION → PARKING LOT)
- **Status:** Parking Lot
- **Category:** code_health
- **Effort:** XS
- **What it is:** Add 1 bullet to nightly Step 5 (security review): "For any new `@router.post` in `billing/`, `billing_usage/`, or `buy-usage`-named routes: verify `block_demo_role` is in `dependencies`. If missing: flag as MEDIUM, fix if <5 LOC, or file GH issue."
- **Evidence:** `block_demo_role` guard has hit 4+ routers historically. `billing_usage.py` POST /buy-usage missed it in 2026-08-07 incident (same nightly that found detached HEAD).
- **Deferred to:** Run 109 candidate (XS effort, high recurrence class).

---

## Carry-Forward from Prior Runs

### orchestrator.py Grandfathered Plan Gap (run 102pm winner — cycle 2)
- **Status:** proposed, autonomous_executable
- **Category:** code_health
- **Effort:** XS
- **What:** `orchestrator.py:238,319` checks `plan in ('professional','enterprise','agent_os')` — missing `'growth'` and `'autopilot'`. Tenants on grandfathered plans receive unbranded automation emails.
- **Fix:** Add `'growth', 'autopilot'` to both plan tuples. 2 one-line edits, 1 file, no migration.
- **Pre-execution:** Read orchestrator.py:225-260 and 310-330. Confirm growth/autopilot in ai_usage_guard.py + plan_gate.py. Run `python -m pytest backend/tests/test_plan_gating_new_plans.py -v`.
- **Deferred to:** Run 108 mandate item 4 (cycle 2). Run 109 direct implementation if still unresolved.

### REFERRAL_REWARD_ENABLED=1 (run 93 winner — pending_human_action)
- **Status:** pending_human_action
- **Requires:** Set env var in Railway Variables → Deploy. 2-minute action.
- **Evidence:** 10/10 checklist items complete (PR #429). Single Railway env-var blocks program launch.
- **Revenue impact:** 3-5x CAC reduction on referral-converted leads.

---

## Run 109 Mandate Preview
1. Step 9H fired in nightly-2026-08-11? `grep 'Step 9H:' ops/routines/logs/nightly-commit-review-2026-08-11.md`
2. KB freshness: did Step 9H detect false-success and comment on GH #403?
3. Detached HEAD guard fired? `grep '1.5\|symbolic-ref\|DETACHED' nightly-2026-08-11.md`
4. orchestrator.py:238+319 — do they include `'growth'` and `'autopilot'`? (cycle 2 → implement directly if still missing)
5. PR #626 status: merged, CI green, or blockers?
6. KB staleness: has kb-autopopulate.yml run succeeded since 2026-07-23? Check `knowledge-base/log.md`.
7. Route-security-guard Step 5 bullet: implement if Step 9H verified firing (XS bonus action).
