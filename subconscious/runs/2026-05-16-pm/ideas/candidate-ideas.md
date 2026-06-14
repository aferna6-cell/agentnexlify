# Candidate Ideas — 2026-05-16-pm (Run 20)

## Context
- Moratorium active: pending=5 (runs 4/7/8/14/19), oldest=30 days (run 4)
- Run 19 winner (SKILL.md Moratorium Escalation Protocol) UNIMPLEMENTED — confirmed by direct read
  (no "## Moratorium Escalation Protocol" section in SKILL.md)
- Zero production commits since May 5 (11 days)
- **Governance mandate fires:** run 19 winning-concept.md §"After SKILL.md Updated — Next Run (Run 20)"
  states: "If SKILL.md NOT updated by run 20: reduce max_pending_approvals 3→2 + create GH milestone"

---

### Idea 1: Governance Threshold Reduction + GH Milestone (governance mandate from run 19)

**Evidence:** Run 19 winning-concept.md §"After SKILL.md Updated — Next Run (Run 20)": "If SKILL.md
NOT updated by run 20: Moratorium mechanism stalled at meta-layer. Governance action: reduce
max_pending_approvals 3→2 + create GH milestone (ideas 4+5)." SKILL.md confirmed NOT updated (read
directly — no "## Moratorium Escalation Protocol" section). GH #169 open but no milestone. 5 pending
items — S-effort group (runs 7+8+14+19) achievable in ~50 min with pre-written implementation sketches.

**Action:** (1) Update governance.json max_pending_approvals 3→2. (2) Create GH milestone
"Moratorium Exit Sprint" with 4 issues: run 19 (SKILL.md, ~10 min), run 8 (pre-commit invariants,
~5 min), run 7 (Widget Sync Guard, ~15 min), run 14 (CI eval, ~20 min). Each issue: effort estimate,
implementation sketch link, moratorium label, priority order.

**Impact:** Threshold change prevents future 5-item buildup (moratorium fires 1 run earlier next time).
Milestone makes exit sprint GitHub-native and human-actionable without requiring knowledge of
subconscious/ directory. Together: new mechanism pressure that doesn't depend on SKILL.md being
updated first.

**Category:** workflow

---

### Idea 2: Repeat Run 19 Recommendation (SKILL.md Update — Third Escalation)

**Evidence:** SKILL.md lacks Moratorium Escalation Protocol section (confirmed). GH #169 created via
improvised behavior (one-time event) — SKILL.md encoding converts to daily sustained loop. 10-min
bounded effort with pre-written implementation sketch (run 18 winning-concept.md §Steps 1-2). Same
recommendation as run 18 + run 19.

**Action:** Formally recommend SKILL.md update again. Escalation framing: 3rd consecutive
recommendation; mechanism unchanged; human must act or moratorium meta-loop stalls permanently.

**Impact:** If implemented, daily GH escalation loop becomes operational. Highest ROI action per
effort. But 2 prior recommendations were ignored. Same mechanism, same human, no new force.

**Category:** workflow

---

### Idea 3: Create GH Milestone Only (Lightweight Version of Idea 1)

**Evidence:** GH #169 open but no organizing milestone. 5 pending items visible in governance.json
but not as a GitHub sprint. S-effort items (runs 7+8+14+19) total ~50 min with pre-written
implementation sketches.

**Action:** Create GH milestone "Moratorium Exit Sprint" only (no governance threshold change). Add 4
issues pointing to implementation sketches.

**Impact:** GitHub-native visibility. Human approver sees a clear, time-boxed sprint. No governance
doc changes. Dominated by Idea 1 which adds threshold reduction at zero extra cost.

**Category:** workflow

---

### Idea 4: Tag Runs 7+8+14 as ai-ready GH Issues (Autonomous Loop Path)

**Evidence:** issue-to-pr-loop polls GH every 15 min per SKILL.md. Runs 7+8+14 are S-effort with
full implementation sketches. If loop is running, could autonomously exit moratorium. Loop status
uncertain: git log shows zero `[issue-to-pr-loop]` or `[auto-nightly]` production commit tags since
May 5.

**Action:** Recommend creating GH issues for runs 7 (Widget Sync Guard), 8 (pre-commit invariants),
14 (CI eval) with `ai-ready` label + implementation sketches. Prerequisite: verify loop is running.

**Impact:** Autonomous moratorium exit if loop running. High upside, uncertain precondition.

**Category:** operational

---

### Idea 5: Sprint Allocation Issue for Run 4 (AI-to-Human Handoff — 30 Days)

**Evidence:** Run 4 is 30 days old. AI-to-Human Handoff v1 = Critical cross-industry gap
(customer-gaps.md all 7 industries). M-effort, 1.5-2 days. No S-effort path. Only human sprint
allocation can implement it. All other pending items are procedural; this one is product.

**Action:** Create urgent GH sprint issue for AI-to-Human Handoff v1 with explicit weekly-check
mechanism: if not started within 7 days, auto-comment escalating to blocker. Route as parallel track
independent of moratorium exit.

**Impact:** Forces highest-value product item onto sprint calendar. Doesn't require moratorium to
exit first. Addresses the 30-day run-4 lag specifically.

**Category:** customer_value
