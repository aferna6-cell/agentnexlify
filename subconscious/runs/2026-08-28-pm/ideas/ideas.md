# Run 115 — Candidate Ideas

Generated: 2026-08-28-pm | Run #115

---

## Idea 1: Step 9L — Dead Service Detector in nightly SKILL.md
**Category:** code_health
**Effort:** S
**Confidence:** HIGH
**Carry-forward status:** First recommendation (parking lot from run 114)

**Evidence:**
- `backend/services/agent_escalation.py`: 88 LOC, 0 grep hits from `backend/routers/`
- Run 114 parking lot: "Step 9L dead service detector (run 115 candidate if agent_escalation.py still unwired)"
- Confirmed this run: grep returns empty for all router imports of agent_escalation
- Pattern: dead service files accumulate silently — nightly scan catches them early

**Why now:**
Evidence confirmed. Implementation sketch ready (grep-based, deterministic). Adds compounding value — catches future orphaned services. S-effort SKILL.md addition.

---

## Idea 2: GH #399 Day 60+ escalation — file quantified blocker issue
**Category:** operational_efficiency
**Effort:** XS
**Confidence:** MEDIUM

**Evidence:**
- GH #399 (AUTOPILOT_GH_TOKEN expired) open 60+ days
- 3 ai-ready issues stalled (#643, #660, #669) blocked by this
- Prior escalation comments at Days 8, 14, 16, 25, 30, 35, 40, 48
- Day 60 is a notable milestone; fresh framing

**Why not winner:**
Pattern: 8+ escalation comments, zero human action over 60 days. This is a bonus action only — not a compounding SKILL.md improvement.

---

## Idea 3: Step 9K stale subconscious PR report — add to nightly log
**Category:** operational_efficiency
**Effort:** S
**Confidence:** MEDIUM

**Evidence:**
- PR #683 still open (draft, 4d+). PR #683 is the subconscious/run-110 branch PR
- 6+ open subconscious draft PRs clogging the PR list
- Step 9K was recommended in run 110 and is pending in PR #683 itself

**Why not winner:**
PR #683 already contains the Step 9K implementation. Duplicating it in SKILL.md without PR merging creates divergence. Step 9L is higher leverage.

---

## Idea 4: Block_demo_role audit — file issue for partners.py missing Depends
**Category:** security
**Effort:** XS
**Confidence:** MEDIUM

**Evidence:**
- GH #669: 95+ routers missing Depends(block_demo_role) on mutating endpoints
- partners.py added in revenue sprint without the guard
- Step 9I sweeps nightly and files issues

**Why not winner:**
Step 9I is already filing issues for this. GH #669 tracks it. Duplicating the alert adds no compounding value.

---

## Idea 5: Step 9J nightly verification — add merge success rate tracking
**Category:** operational_efficiency
**Effort:** XS
**Confidence:** MEDIUM

**Evidence:**
- Step 9J fix live (run 114): allows merge on unknown
- No data yet on whether it works (no nightly since fix landed)
- Run 116 mandate will check this naturally

**Why not winner:**
Too early to evaluate. First nightly with fix is tonight (2026-08-28). Run 116 mandate already covers verification. Wait for data.
