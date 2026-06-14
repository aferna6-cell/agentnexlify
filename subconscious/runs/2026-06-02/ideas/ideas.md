# Ideas — 2026-06-02 (Run 46)

## Evidence Summary

Zero production commits since run 45 (2026-06-01-pm). Moratorium day 32, pending 15 (unchanged).
Run 45 winner (Item A: scope em-dash check + wire Check 10) unimplemented — nightly 2026-06-02
confirms human-execute required, zero autonomous action taken. Human present in interactive
session. All pending items confirmed missing: Check 10 absent from pre-commit (grep = 0),
`check_project_invariants.py` exits 1 on 5 JSX em-dash violations (GH #194), email_sequences.py
1255L (run 41, day 3), check-widget-sync.sh MISSING (run 7, day 39+), lead-qualifier-eval.yml
MISSING (run 14, day 28+). NEW FINDING: `backend/services/billing.py` not found at expected
path — grep exits with no output, exit 2. GH #181 (AMOUNT_TO_PLAN missing 15000+25000) has been
a standing action 26+ days with 2 failed fix attempts. If billing constants moved during the
god-class refactor (PR #180, 13 new service files), all previous implementation sketches target
the wrong file. customer-gaps.md: AI-to-Human Handoff still Critical. skill-discovery last
report: 2026-05-25.

---

### Idea 1: Execute Item A — Scope em-dash check + wire Check 10 as pre-commit guard

**Evidence:** Run 45 winner unimplemented. Nightly 2026-06-02 confirms human-execute required
and no autonomous path exists. `check_project_invariants.py` exits 1 on 5 JSX em-dash
violations. `grep -c "check_project_invariants" scripts/hooks/pre-commit` = 0. Human present
in interactive session. Implementation sketch pre-written in runs/2026-06-01-pm/winning-concept.md.

**Action:** (1) Edit `check_project_invariants.py` — add `_skip_ui_copy = {".jsx", ".tsx"}` +
`continue` guard in `check_website_copy_avoids_em_dashes()` (~3 min). (2) Verify exit 0.
(3) Add Check 10 block to `scripts/hooks/pre-commit` before existing Check 11 (~3 min). (4) Commit.

**Impact:** Check 10 live on every future commit. GH #194 closed. Run 8 (day 37) + Run 22
(day 15) both resolved. Pending 15→13. Moratorium continues but two items close.

**Category:** workflow / code_health

---

### Idea 2: Investigate billing.py location post-god-class-refactor

**Evidence:** `grep -n "AMOUNT_TO_PLAN" backend/services/billing.py` exits with no output
(exit 2 — file not at expected path or file empty). PR #180 (2174732) added 13 new service
files (5038+ insertions). Two failed GH #181 fix attempts (c72b535 May 22, 1eaaeec May 23)
both missed 15000+25000 entries — if file moved, previous sketches target wrong location.
Check 11 (billing-constant-guard, 061582c) fires WARNING confirming the gap is real but
does not reveal the file's current path.

**Action:** Run `find backend/ -name "*billing*" -type f` + `grep -rn "AMOUNT_TO_PLAN"
backend/`. If entries already contain 15000+25000 in a new file: close GH #181 as resolved.
If file relocated: update implementation sketch with correct path. 5 min investigation only.

**Impact:** Unblocks a 26-day standing action. Explains two failed fix attempts. Either
reveals correct target path or closes GH #181 as already fixed.

**Category:** code_health

---

### Idea 3: Extend nightly autonomous scope to cover CI YAML creation — enable Item D tonight

**Evidence:** Run 45 backlog: "Add Item D to autonomous scope as run 46 winner after Item A
confirms." Item A NOT confirmed. lead-qualifier-eval.yml MISSING 28 days (run 14 winner).
Nightly channel successfully extended scope for pre-commit bash additions (4226ef4). CI YAML
addition is purely additive — new file creation only, no production code logic.

**Action:** Update nightly-commit-review SKILL.md autonomous scope to include new
`.github/workflows/*.yml` creation. Add AUTONOMOUS-EXECUTABLE label + inline
lead-qualifier-eval.yml content patch to winning-concept.md.

**Impact:** If nightly executes: closes run 14 winner (28 days), wires golden eval harness
to CI. Pending 15→14.

**Category:** operational

---

### Idea 4: Mark Item B as AUTONOMOUS-EXECUTABLE — widget sync guard + pre-push wire

**Evidence:** scripts/check-widget-sync.sh MISSING 39+ days (run 7 winner). Widget assets
confirmed byte-identical (invariants PASS). Nightly autonomous scope now covers pre-commit
bash additions (4226ef4). check-widget-sync.sh is ~15 lines bash (simple diff command).
Pre-push hook addition = 3 lines bash.

**Action:** Write full check-widget-sync.sh content in winning-concept.md + pre-push
addition block. Label AUTONOMOUS-EXECUTABLE. Extend nightly scope to cover new bash script
creation in `scripts/` + pre-push hook entries.

**Impact:** If nightly executes: closes run 7 winner (39 days). Protects three widget
copies. Pending 15→14.

**Category:** code_health

---

### Idea 5: Create moratorium exit GH sprint checklist issue

**Evidence:** Run 45 bonus action (GH Sprint Checklist Issue) not executed. 15 pending
items, moratorium day 32. governance.json is 757 lines; a single GH checklist issue is
GitHub-native and surfaces in notifications. Human present to create it.

**Action:** Create GH issue: "Moratorium Exit Sprint — remaining human-required items"
with 5 checkboxes: GH #181, Item A, Item B, Item D, email_sequences split.

**Impact:** GitHub-native actionable checklist. Reduces navigation friction. 5 min effort.

**Category:** workflow
