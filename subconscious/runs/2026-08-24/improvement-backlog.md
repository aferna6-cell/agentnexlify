# Improvement Backlog — Run 109 (2026-08-24)

Ideas ranked by impact × confidence × effort. Winner implemented this run. Others deferred.

---

## #1 — Step 9J: Dependabot Auto-Merge (WINNER — IMPLEMENTED)

**Category:** operational  
**ROI:** HIGH — indefinite security dep bump coverage, 15 min/week saved  
**Status:** Implemented 2026-08-24 (autonomous-executable, 1st carry-forward mandate)  
**Notes:** Step 9J block live in SKILL.md. Verify next nightly for "Step 9J:" log line.

---

## #2 — Step 9K: Stale Autonomy PR Closer (report-only variant)

**Category:** operational  
**ROI:** MEDIUM — human visibility into PR debt, no auto-close risk  
**Effort:** XS  
**Status:** Run 110 candidate  
**Evidence:** 5 subconscious PRs open as of run 102 (#575, #606, #611, #613, #626). PR dedup guard prevents new duplicates but existing idle drafts persist. run_109_mandate named Step 9K as candidate.  
**Action:** Add Step 9K block to SKILL.md: list open PRs with head branch starting `subconscious/`, age >14d, no commits last 7d, no review activity. Log count. Post comment on oldest if >21d. No auto-close.  
**Governance trigger:** Implement as winner in run 110 if ≥3 subconscious PRs still open AND Step 9J verified firing.

---

## #3 — Middleware-Level block_demo_role FastAPI Guard

**Category:** code_health  
**ROI:** HIGH — closes 97 violations at once, prevents regression on new routers  
**Effort:** M  
**Status:** Deferred — human-approval required, wrong queue (GH #399 blocks ai-ready loop)  
**Evidence:** GH #669 (97/97 routers missing block_demo_role, filed 2026-08-20). One-off fixes (#643 appointment_briefs, #661 scoring_config) proved class problem with no systemic guard.  
**Action:** Human comments middleware approach on GH #669 — FastAPI middleware or app-level dependency injection at main.py. Include implementation sketch. Not a nightly automation candidate.  
**Unblocked by:** Human action on GH #669.

---

## #4 — GH #403 Diagnostic Follow-Up Comment

**Category:** operational  
**ROI:** MEDIUM — may unblock KB autopopulate (32d+ stale), which feeds AI chat answers  
**Effort:** XS  
**Status:** Deferred — run 107 bonus comment already posted with setup path; adding more without human engagement is noise  
**Evidence:** GH #403 ANTHROPIC_API_KEY + SUPABASE_URL missing in GH Actions. KB last run 2026-07-23 (32 days stale). Run 107 posted targeted comment. No human response.  
**Action:** If human does not action #403 by run 111, re-escalate with a specific ask: "Reply with the GH Actions run URL from kb-autopopulate.yml so we can see the error message."  
**Hold until:** Run 111 if no progress.

---

## #5 — Step 9K Auto-Close Variant (parking lot)

**Category:** operational  
**ROI:** MEDIUM — cleaner PR list, eliminates draft debt  
**Effort:** S  
**Status:** Parking lot — risk outweighs report-only variant  
**Evidence:** Auto-close risks closing a PR human intended to keep. Report-only (#2 above) achieves 80% of benefit with 0% risk.  
**Action:** Promote only if report-only variant runs 2+ cycles and human explicitly requests auto-close.

---

## Standing Blockers (not this run's job, but tracked)

| Issue | Status | Age |
|-------|--------|-----|
| GH #399 AUTOPILOT_GH_TOKEN expired | OPEN | Day 41+ |
| GH #403 ANTHROPIC_API_KEY missing in GH Actions | OPEN | 32d stale KB |
| GH #669 97/97 routers missing block_demo_role | OPEN | Filed 2026-08-20 |
| Dependabot PRs #629/#630/#631/#649/#665/#666 | Should auto-merge next nightly | 4+ weeks |
