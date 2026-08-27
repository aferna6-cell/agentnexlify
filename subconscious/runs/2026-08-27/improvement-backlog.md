# Improvement Backlog — Run 114 (2026-08-27)

Ideas ranked by impact × confidence × effort. Winner autonomous-executable this run.

---

## #1 — Fix Step 9J: Handle `mergeable_state: unknown` (WINNER — IMPLEMENT THIS RUN)

**Category:** operational  
**ROI:** HIGH — unblocks 19+ Dependabot PRs, restores CVE window to <24h permanently  
**Effort:** XS  
**Status:** Autonomous-executable — SKILL.md edit, nightly will execute on 2026-08-28  
**Notes:** GH Actions dark since 2026-07-20 (GH #500). `"clean"` state impossible. Must allow `unknown` → attempt merge + handle errors. See winning-concept.md for exact replacement logic.

---

## #2 — Step 9K: Stale Autonomy PR Closer (pending human approval, PR #683)

**Category:** operational  
**ROI:** MEDIUM — closes superseded subconscious draft PRs, escalates stale ones  
**Effort:** S  
**Status:** Recommended in Session 2 (2026-08-25) on branch subconscious/run-110. Requires human approval to implement. 6 open subconscious PRs meet ≥3 threshold. Promote to autonomous-executable immediately on human approval of PR #683.  
**Action:** Human approves PR #683 → nightly runs Step 9K → expected to close #575, #626 (superseded) and comment on oldest remaining.

---

## #3 — Step 9L: Dead Service Detector (run 111 candidate)

**Category:** code_health  
**ROI:** MEDIUM — systematic prevention of dead service accumulation (agent_escalation.py is 2nd case)  
**Effort:** S  
**Status:** Parking lot. Promote to run 111 winner if: (a) agent_escalation.py still has 0 router callers, AND (b) grep exclusion pattern validated (exclude automation/scheduled/, utils, helpers, __init__.py, *_test.py).  
**Governance trigger:** Run 111 candidate if both conditions met.

---

## #4 — Step 9D Enhancement: Escalate ai-ready Issues Stalled >14d

**Category:** workflow  
**ROI:** MEDIUM — automated pressure on loop blockage (#399 blocker)  
**Effort:** S  
**Status:** Deferred. GH #399 (AUTOPILOT_GH_TOKEN) is root blocker — step 9D comments are noise until the loop itself is unblocked. Re-evaluate run 112 if #399 still open at Day 60+.

---

## #5 — File GH Issue to Wire agent_escalation.py

**Category:** code_health  
**ROI:** LOW-MEDIUM  
**Effort:** XS  
**Status:** Deferred to nightly via Step 9I (nightly will file if no existing issue found). Not a subconscious winner — one-off issue filing is nightly scope.

---

## Standing Blockers (human-only)

| Issue | Status | Age |
|-------|--------|-----|
| GH #399 AUTOPILOT_GH_TOKEN expired | OPEN | Day 54+ |
| GH #684 brain connector stale | OPEN | 35d |
| GH #669 97/97 routers missing block_demo_role | OPEN | 7d |
| GH #500 GH Actions dark | OPEN | 38d — ROOT CAUSE of Step 9J 0 merges |
| Dependabot PRs 19+ aging | Will unblock after Step 9J fix | 31d oldest |
