# Ideas — Run 52 (2026-06-06)

## Evidence Digest

- check_project_invariants.py exits 0 (all 6 PASS). Item A (Check 10) pre-condition met.
- Item A will auto-wire at 2:37 AM on 2026-06-07 per SKILL.md §Item A inline patch.
- Item B (check-widget-sync.sh) MISSING 44 days. Root cause confirmed: nightly scope covers SKILL.md *creation* only, not *modification*. Run 50 AUTONOMOUS-EXECUTABLE blocked by this gap.
- PR #183 (GH #181 billing fix) 12+ day draft, confirmed path (backend/routers/billing.py), morning digest endorsed merge.
- email_sequences.py 1255L (run 41, 8 days pending). Blocked by GH #181 as prerequisite.
- Moratorium day 37, 15 pending (many superseded). No production code commits 1 day.
- No new nightly for 2026-06-06 yet. Next nightly: 2:37 AM 2026-06-07.

---

### Idea 1: Fix nightly scope gap — add additive SKILL.md modification bullet
**Evidence:** Run 50 AUTONOMOUS-EXECUTABLE winner is blocked: nightly scope line 65 says "New `.claude/skills/*/SKILL.md` *creation*" — run 50 requires *modification* of existing nightly SKILL.md. 44-day check-widget-sync.sh gap traces directly to this missing scope bullet. Prior scope-extension pattern (runs 40→43→47) each delivered in next nightly cycle.
**Action:** Add 1 bullet to `.claude/skills/nightly-commit-review/SKILL.md` LOW-risk scope section: "**Additive text additions to existing `.claude/skills/*/SKILL.md`** when winning-concept.md provides verbatim patch content with AUTONOMOUS-EXECUTABLE, change is purely additive (append-only, no deletions), and the skill is NOT nightly-commit-review itself." Then add Item B inline content block to nightly SKILL.md so it fires in next cycle.
**Impact:** Converts Item B from "blocked autonomous" to "auto-executes 2026-06-07 at 2:37 AM." Closes 44-day gap. Fixes structural scope definition bug that blocked 2+ autonomous runs.
**Category:** workflow

---

### Idea 2: Merge PR #183 (run 51 1-day follow-up)
**Evidence:** 12+ day draft PR exists. billing.py at backend/routers/billing.py confirmed (run 47). Check 11 fires WARNING confirming AMOUNT_TO_PLAN missing 15000+25000. Morning digest endorsed merge. CI gate (pr-check.yml + pre-commit + pre-push) guards the merge.
**Action:** Review PR #183 diff, verify CI green, `gh pr merge 183 --squash`, grep + pytest verify.
**Impact:** Closes GH #181 (50-day bug), unblocks email_sequences split (run 41), reduces human-required pending by 1.
**Category:** code_health

---

### Idea 3: email_sequences.py split via /god-class-splitter
**Evidence:** 1255L confirmed. 3 clean concerns (CRUD/enrollment/processor). god-class-splitter SKILL.md (e848b87) + post-split-test-repair SKILL.md (d481799) ready. GH #112/#113 N+1 queries unblocked post-split. Run 41 winner 8 days unimplemented. Prerequisite: PR #183 merge.
**Action:** Invoke `/god-class-splitter` on email_sequences.py. Step 0: merge PR #183 first.
**Impact:** Reduces 1255L → 3 focused files (<400L each). Enables GH #112 N+1 fix. Improves test isolation.
**Category:** code_health

---

### Idea 4: AI-to-Human Handoff v1 via Agent OS
**Evidence:** 51 days pending (run 4). Critical gap all 7 industries. Agent OS shipped (os_outbound_mirror.py, 152 tests, merged PR #188 2026-05-27). Scope reduced from ~3 days to ~1 day. Run 38 winner with MEDIUM confidence. Moratorium parallel track authorized since run 20.
**Action:** Implement explicit trigger detection in widget_chat.py, create handoff_requests migration, route SMS via os_outbound_mirror.send_sms().
**Impact:** Fills Critical customer gap across all 7 verticals. Differentiates from GoHighLevel.
**Category:** customer_value

---

### Idea 5: Governance audit — consolidate superseded items, determine true pending count
**Evidence:** governance.json shows 15 pending. Run 28 found 12→4 after audit. Since run 28, 15+ new active_directions added (many superseded). True human-required pending unclear. max_pending_approvals=2 but no one knows what "2 true pending" looks like.
**Action:** Audit all active_directions entries. Mark runs 21/28/29/35 as superseded by more recent entries. Mark run 30 (billing constants tests) as subsumed by Check 11 (implemented). Recalculate true pending count.
**Impact:** May reveal moratorium already-effectively-exited. Removes cognitive load. Ensures governance.json reflects reality.
**Category:** workflow
