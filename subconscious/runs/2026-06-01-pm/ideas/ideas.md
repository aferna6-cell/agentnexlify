# Ideas — Run 45 (2026-06-01-pm)

## Evidence Summary

Run 44 winner (scope em-dash check to skip .jsx/.tsx) labeled AUTONOMOUS-EXECUTABLE but
NOT executed by nightly 2026-06-01. Root cause: nightly's autonomous scope (4226ef4) covers
pre-commit bash additions, not Python script edits. Item A remains blocked.
check_project_invariants.py exits 1 on 5 JSX em-dash violations.
email_sequences.py 1255L, day 4 unimplemented (GH #181 prerequisite open).
Moratorium day 31, 14 pending, oldest day 47. Human present in interactive session.

---

### Idea 1: Execute scope fix + Item A wiring as single human-committed step (~10 min)

**Evidence:** Run 44 implementation sketch is fully written. Item A inline patch is staged in
nightly SKILL.md. Nightly confirmed Python script edits are NOT in its autonomous scope
(confirmed by 0 executions across 3 cycles). Human is present in this session — the highest
probability implementation window. The scope fix (3 lines Python) + Item A wiring (3 lines
bash in pre-commit) are both zero-risk edits with no blockers.

**Action:**
1. Edit `scripts/check_project_invariants.py`: modify `check_website_copy_avoids_em_dashes()`
   to skip `.jsx` and `.tsx` suffixes
2. Run `python3 scripts/check_project_invariants.py` — expect all 6 PASS
3. Add 3-line Check 10 block to `scripts/hooks/pre-commit`
4. Commit: `ci(invariants): scope em-dash to skip JSX/TSX + wire as pre-commit Check 10`
5. Closes GH #194, run 8 (day 37), run 22 (day 15)

**Impact:** Item A confirmed implemented — moratorium pending 14→13. Check 10 protects
backend invariants on every commit going forward. Unlocks next autonomous item (Item D).

**Category:** workflow / code_health

---

### Idea 2: Add Item D (lead-qualifier-eval.yml) to AUTONOMOUS-EXECUTABLE scope

**Evidence:** Run 44 explicitly flagged: "after Item A confirms, propose Item D for autonomous
scope." Item D = create `.github/workflows/lead-qualifier-eval.yml` (Monday cron + PR trigger).
Run 14 winner, 27 days pending. The nightly has created new files (SKILL.md, bash additions).
A new `.yml` file in `.github/workflows/` is additive, LOW-risk, and structurally similar to
prior autonomous deliverables. No conflict with other sprint items.

**Action:** Update governance.json Item D status to `pending_autonomous` + `autonomous_executable: true`.
Add directive to nightly-commit-review SKILL.md: new `.github/workflows/lead-qualifier-eval.yml`
additions qualify as LOW-risk autonomous when `autonomous_executable: true` present. Include
inline YAML template in SKILL.md (Monday 8:30 cron + PR trigger, LEAD_QUALIFIER_AGENT_ID secret).

**Impact:** Item D executes next nightly. moratorium pending 14→12 (Items A + D). Closes
Issue #110. Eval harness gates weekly regressions.

**Category:** workflow / operational

---

### Idea 3: Create GitHub Sprint Checklist Issue — 5 human-required items, 1 decision

**Evidence:** Moratorium at 47 days with 5 human-required items scattered across governance.json
active_directions. No single actionable surface exists. GH #193 receives moratorium escalation
comments but doesn't enumerate what human must DO. The bottleneck has been commitment + friction,
not information. A single GH issue with a linked checklist + 5-min / 20-min / 15-min / 2h / 1d
effort labels converts 5 decisions into 1: "open this issue and start at the top."

**Action:** Create GH issue "feat: Moratorium Exit Sprint — 5 items, ~1 day total" with
numbered checklist:
1. GH #181 billing fix — 15 min (link to winning-concept.md)
2. Item A scope fix + Check 10 — 10 min (link to run 44/45 winning concept)
3. Item B check-widget-sync.sh — 15 min (link to run 7 winning concept)
4. Item D lead-qualifier-eval.yml — 20 min (link to run 14 winning concept)
5. email_sequences.py split — 2h (link to run 41 winning concept)

**Impact:** Single GH issue → single approval → sprint sequence is clear. Prior runs attempted
this via subconscious directory knowledge (run 23 sprint PR, run 29 GH issue) — those failed
because they required knowing the implementation sketches. This links directly.

**Category:** workflow

---

### Idea 4: Fix GH #181 billing constants directly (HUMAN-REQUIRED, ~15 min)

**Evidence:** billing.py AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional for 32+
days. Check 11 fires WARNING on every commit as reminder. 4 consecutive recommendation runs
without implementation triggered rejected_paths entry. Cannot be chosen as standalone winner.
(Blocked by governance.)

**Action:** CANNOT BE WINNER — rejected_paths entry. Listed for completeness only.

**Impact:** N/A

**Category:** code_health — REJECTED, governance.json rejected_paths

---

### Idea 5: Extend nightly autonomous scope to cover Python script edits (scripts/check_*.py)

**Evidence:** Run 44 AUTONOMOUS-EXECUTABLE label failed because nightly's scope covers bash
additions and SKILL.md creation, not Python script edits. Run 44 → run 45 → another scope
extension is a meta-loop pattern (runs 37→38→39→40 were a similar meta-chain). Adding Python
script edit capability to nightly is higher risk than prior expansions (bash/YAML/SKILL.md).
A Python script edit could introduce bugs in invariant checking.

**Action:** Extend nightly-commit-review SKILL.md to include single-file Python edits in
`scripts/check_*.py` when autonomous_executable: true + pre-condition verified. Specify scope:
only additive changes (new SKIP list entries), not logic changes.

**Impact:** Enables run 44-class changes to be autonomous. Reduces scope-fix bottleneck.

**Category:** workflow

**NOTE:** Risk concerns — this extends the blast radius of nightly autonomous changes into
Python logic files. Strongly WEAKENED vs Idea 1 (human executes directly in 10 min).
