# Candidate Ideas — Run 19 (2026-05-16)

## Evidence Digest

- **Zero production commits in 11 days** (since 72f8204, 2026-05-05). All commits: subconscious
  artifacts + nightly ops logs only.
- **GH issue #169 created today** by nightly review — moratorium escalation fired via improvised
  behavior. nightly-commit-review SKILL.md does NOT contain Moratorium Escalation Protocol.
  Improvised once; may not repeat without formal encoding.
- **Moratorium: 5 pending items, oldest 30 days** (run 4, AI-to-Human Handoff v1). S-effort
  items: run 18 (SKILL.md, 0 days), run 14 (eval CI, 11 days), run 8 (invariants pre-commit,
  21 days), run 7 (Widget Sync Guard, 22 days).
- **scripts/check-widget-sync.sh MISSING** (22 days, 5 consecutive nightly reviews confirm).
- **.github/workflows/lead-qualifier-eval.yml MISSING** (11 days).
- **check_project_invariants.py not wired to pre-commit** (21 days; script passes 6/6 checks).
- **Zapier API key issue #107** still open (16+ days); bug-patterns.md entry active.
- **customer-gaps.md**: AI-to-Human Handoff remains #1 cross-industry Critical gap.

---

### Idea 1: Formalize Moratorium Escalation Protocol in nightly-commit-review SKILL.md
**Evidence:** GH #169 created today (2026-05-16 nightly run — ops log `3467528`). SKILL.md
has no "## Moratorium Escalation Protocol" section and no step 10A. Agent improvised today
by reading governance.json directly; context-dependent behavior is fragile. Run 18
winning-concept.md §Steps 1-2 provides exact SKILL.md content to add.
**Action:** Add "## Moratorium Escalation Protocol" section and step 10A to
`.claude/skills/nightly-commit-review/SKILL.md`. Content already written in
`subconscious/runs/2026-05-15-pm/winning-concept.md`. ~10 min edit.
**Impact:** Ensures GH escalation fires every night moratorium is active (daily comment
updates on #169 showing current pending ages + implementation estimates). One-time improvised
event → sustained nightly pressure. Completes run 18 winner.
**Category:** workflow

---

### Idea 2: Create ai-ready GH Issues for S-effort Pending Items (runs 7+8+14)
**Evidence:** issue-to-pr-loop polls GH every 15 min for issues tagged `ai-ready`. Runs 7,
8, 14 have complete implementation sketches in winning-concept.md files. Human implementation
velocity = 0 commits/11 days. Autonomous loop runs (nightly review fires 5 consecutive
nights = same infrastructure). Routing to automation bypasses human-availability bottleneck.
**Action:** Create 3 GH issues (Widget Sync Guard, invariants pre-commit, eval CI) tagged
`ai-ready,ai-subconscious`, each with implementation sketch from relevant winning-concept.md.
**Impact:** Autonomous loop picks up issues → implements S-effort items without human time.
Could drop pending 5→2 within hours. Moratorium could exit if loop is running.
**Category:** workflow

---

### Idea 3: Widget 3-Copy Sync Guard (run 7 — sixth escalation, moratorium protocol)
**Evidence:** scripts/check-widget-sync.sh MISSING for 22 days. Five consecutive runs (15-18
plus current) recommended this. Oldest S-effort pending item by days. Nightly reviews May
11-15 confirm all 3 widget copies IN SYNC — no active divergence, but guard missing means
future edits unprotected.
**Action:** Create `scripts/check-widget-sync.sh` (diff all 3 widget copies, FAIL on
diverge), wire into `scripts/hooks/pre-push`, fix CLAUDE.md Invariant #4 ("2 copies" →
"3 copies"). ~15 min.
**Impact:** Prevents future widget byte-divergence. Drops pending 5→4. S-effort.
**Category:** code_health

---

### Idea 4: Reduce Governance max_pending_approvals Threshold 3→2
**Evidence:** Moratorium now at 5 pending (vs trigger threshold 3). The 3-threshold allowed
3 items to accumulate BEFORE triggering moratorium. Runs 7+8+14 all landed before moratorium
kicked in. Reducing to 2 triggers future moratoriums earlier, preventing multi-item backlog.
**Action:** Update `subconscious/state/governance.json` `config.max_pending_approvals` from
3 to 2. Update moratorium_config lift_condition text.
**Impact:** Future moratoriums trigger with 2 pending items instead of 3. Prevents 5-item
pile-ups. Zero risk — governance parameter only.
**Category:** operational

---

### Idea 5: Create GitHub Milestone for Moratorium Exit Sprint
**Evidence:** GH #169 now exists — first external (GH) visibility of moratorium. Five pending
items with no consolidated tracking. No GH milestone links them. Run 4 (AI-to-Human Handoff,
30 days) requires sprint allocation — needs milestone to force planning conversation.
**Action:** Create GH milestone "Subconscious Moratorium Sprint 2026-05" with target date.
Add all 5 pending items to milestone. Link to #169. Sprint owner: human.
**Impact:** Forces sprint planning. Makes moratorium exit trackable with a deadline.
**Category:** operational
