# Candidate Ideas — Run 18 (2026-05-15-pm)

**Context:** Run 17 set a binding governance mandate: if Widget 3-Copy Sync Guard is still
unimplemented at run 18, winner MUST switch to Automated Moratorium Escalation Hook.
Widget Sync Guard confirmed MISSING as of this run. Mandate fires.

---

### Idea 1: Automated Moratorium Escalation Hook
**Evidence:** Run 17 governance boundary condition explicitly mandated this as run 18 winner
if Widget Sync Guard unimplemented. Confirmed: scripts/check-widget-sync.sh MISSING
(5 consecutive nightly reviews: May 11-15 all log "MISSING"). 4 consecutive subconscious
moratorium runs with same winner (Widget Sync Guard, runs 15-16-17-18AM). Zero
implementation commits in 10 days (since 72f8204 on May 5). Current mechanism
(winning-concept.md in git) requires humans to browse git history — low attention conversion.
**Action:** Update `.claude/skills/nightly-commit-review/SKILL.md` Scheduled Task Prompt
to add moratorium escalation step: read governance.json, check moratorium_active + pending
count + oldest age, create GH issue via mcp__github__create_issue (or add comment if issue
already exists) with table of pending items + implementation estimates + link to winning-concept.md.
Also add a "## Moratorium Status" section to the nightly report output structure.
**Impact:** Creates visible pressure in GitHub (where humans spend implementation time).
Closes the recommendation→implementation feedback gap. Converts silent subconscious
runs into actionable GH notifications. Precedent: nightly review already creates GH
issues for MEDIUM/HIGH bugs — moratorium escalation is same mechanism, new trigger.
**Category:** workflow

---

### Idea 2: Widget 3-Copy Sync Guard
**Evidence:** scripts/check-widget-sync.sh MISSING. 21 days since first recommendation (run 7,
April 24). All 3 copies confirmed byte-identical (md5: 997eb698, May 15 nightly PASS).
S-effort, zero blockers. Implementation sketch unchanged since run 15.
**Action:** Create scripts/check-widget-sync.sh + wire pre-push hook + fix CLAUDE.md
Invariant #4 (2 → 3 widget paths).
**Impact:** Preventative guard against future widget sync divergence. Any widget edit
without guard can silently diverge across 3 copies.
**Category:** code_health
**GOVERNANCE NOTE:** Per run 17 mandate, cannot be WINNER this run (4-consecutive-run
threshold reached). Remains valid implementation task — demoted to Bonus step.

---

### Idea 3: PR Queue Auto-Merge for Safe Patch Deps
**Evidence:** Morning digest 2026-05-15 shows 4 PRs safe to merge without testing:
#163 (@typescript-eslint/parser 8.58→8.59), #164 (@playwright/test 1.59→1.60),
#102 (youtube-transcript-api patch), #103 (python-multipart 0.0.26→0.0.27).
All are patch bumps, 1-18 days old. PR #80 (onboarding-v2 Week 1, 22 days) blocking
14+ dependent issues. PR queue drag adds context-switch cost to human implementation.
**Action:** Update morning-digest skill to include auto-merge directive for PRs where:
(1) patch-only version bump, (2) CI green, (3) no code changes, (4) < 20 days old.
**Impact:** Clears PR queue without human touch. Reduces context-switch overhead.
**Category:** workflow

---

### Idea 4: Email Sequences N+1 Query Fix
**Evidence:** GH #112 (opened 2026-05-02, 13 days): list_enrollments makes 1 DB call
per enrollment = 1001 queries per 1000 enrollments. list_sequences: 2 DB calls per sequence.
bug-patterns.md 2379 lines includes this. Parking lot ROI 2.3. Email automation
feature (onboarding V2 sprint active).
**Action:** Fix list_enrollments and list_sequences in backend/routers/email_sequences.py
to use bulk .in_() queries. Add regression test.
**Impact:** Eliminates 1000x query amplification as email adoption scales. M-effort.
**Category:** code_health

---

### Idea 5: Wire check_project_invariants.py into pre-commit (run 8)
**Evidence:** 037865f added script April 25. Script passes all 6 checks (confirmed May 5
after em-dash cleared by 8f680e8). Day 20 pending. S-effort, 8-line pre-commit block.
**Action:** Add Check 10 block to scripts/hooks/pre-commit calling python3
scripts/check_project_invariants.py. Closes run 8.
**Impact:** Blocks commits using tenant_id on leads, lead_stage, service_interest naming
violations. ~5 min effort.
**Category:** code_health
**GOVERNANCE NOTE:** Active direction (moratorium item), not a new idea. Should execute
as Bonus A alongside winner, not as winner itself.
