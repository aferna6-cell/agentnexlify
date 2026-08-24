# Run 110 — Ideas (2026-08-24-pm)

## Evidence signals
- Step 9J confirmed in SKILL.md (lines 392-411) — but major-version gate ABSENT
- PR #674 description claimed gate was included — code does not match claim
- memory.jsonl line 108 (run 109 2nd entry) says "major-version safety gate confirmed" — FALSE
- First Step 9J nightly execution: 2026-08-25 at 2:37 AM (tomorrow)
- Open major-version Dependabot PRs: #586/#591/#593 (react 18→19), #598 (stripe v11→v15)
- Without gate: these merge automatically tomorrow night → production breaks
- All 20 GH Actions scheduled workflows unscheduled today (334d32c + 4c45e67)
- Replacement substrate (ops/routines/logs/) has zero monitoring mechanism
- GH #669: 95+ routers missing block_demo_role (PR #653, 12d draft, unmerged)
- GH #403: KB 32+ days stale, ANTHROPIC_API_KEY missing
- GH #399: AUTOPILOT_GH_TOKEN expired Day 46+
- Open subconscious PRs: #626 (22d), #575 (32d) — #674 now merged

## Candidate ideas

### Idea 1: Add major-version safety gate to Step 9J — XS edit, time-critical
**Category:** code_health
**Effort:** XS (~12 lines in SKILL.md)
**Urgency:** CRITICAL — Step 9J fires for the first time tomorrow (2026-08-25 02:37 AM)
**Evidence:** SKILL.md step 2 has checks (a) CI, (b) review requests, (c) labels. Missing (d) major-version. PR #674 body claimed gate was present; direct read proves it is not. React 18→19 (#586/#591/#593) and stripe v11→v15 (#598) are live open PRs that would pass all existing checks and be merged. Autonomous-executable via proven nightly SKILL.md channel.
**Action:** Insert step 2d between labels check (line 403) and merge block (line 404): parse PR title for "from X.Y.Z to A.B.C" or "bump PKG from X to Y" pattern; extract major versions; if new_major > old_major → skip with log line. Update step 4 log to include "major-version" as skip reason.

### Idea 2: Step 9K — Stale subconscious PR report in nightly SKILL.md
**Category:** workflow_efficiency
**Effort:** S
**Urgency:** Medium — mandate condition met (≥3 subconscious PRs open), but non-critical
**Evidence:** PR #575 (32d), #626 (22d) still open. PR queue noise. Run 109 mandate specified "report-only if ≥3 open". Now that #674 merged, condition marginally met.
**Action:** Add Step 9K block to nightly: list open draft PRs with "subconscious" or "run-" head branches, log count, comment on oldest if >21d with "stale — consider closing".
**Gap:** Lower urgency than Idea 1. Parking lot.

### Idea 3: Step 9L — Replacement substrate health monitor in nightly SKILL.md
**Category:** operational
**Effort:** S
**Urgency:** Medium — substrate migrated TODAY; too new to verify normal pattern
**Evidence:** 20 GH Actions workflows unscheduled (334d32c + 4c45e67). Decision doc: planning/decisions/2026-08-24-actions-replacement-substrate.md. No Routine monitoring ops/routines/logs/. Substrate could fail silently.
**Action:** Add Step 9L block: check ops/routines/logs/ for expected daily files, alert if any routine log older than 48h.
**Gap:** Substrate only hours old. Wait 1-2 runs to establish baseline. Parking lot.

### Idea 4: GH #669 middleware comment — architecture sketch
**Category:** code_health
**Effort:** XS (comment only)
**Urgency:** Low
**Evidence:** PR #653 (12d draft) proposes per-router approach. 95+ endpoints still unguarded.
**Gap:** Non-structural comment without implementation path. Subconscious recommends, doesn't implement router changes. WEAKENED.

### Idea 5: GH #403 targeted escalation comment (Day 32+)
**Category:** operational
**Effort:** XS
**Urgency:** Low — 4+ prior comments with no human action
**Gap:** Same mechanism run 4+ times. Compounding comment count adds noise. KILLED — diminishing returns.

## Ranking
1. **Idea 1** (major-version gate) — WINNER: time-critical, autonomous-executable, XS effort
2. **Idea 3** (Step 9L) — parking lot: valid but substrate too new
3. **Idea 2** (Step 9K) — parking lot: mandate met but non-critical
4. Idea 4 — weakened
5. Idea 5 — killed
