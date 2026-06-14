# Ideas — Run 2026-05-29-pm (Run 40)

Generated from evidence: git log 3d, nightly logs, bug-patterns, customer-gaps, skill-discovery.

---

### Idea 1: Fix Nightly Autonomous Channel — Add SKILL.md Creation to LOW-Risk Scope
**Evidence:** `dc5ef8e` (nightly 2026-05-28) explicitly labeled run 36 winner "docs only" and skipped creating post-split-test-repair SKILL.md despite the AUTONOMOUS-EXECUTABLE label. Same failure on run 39's nightly cycle (061582c implemented Check 11 code but not SKILL.md). Code changes (Check 11 bash block, 72f8204 JS silent catch) succeed 100% via nightly. Pure .md file creation fails 100% — 2 consecutive cycles missed.
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` to add explicit rule: "When `subconscious/winning-concept.md` contains `AUTONOMOUS-EXECUTABLE`, creating a new `.claude/skills/*/SKILL.md` file is LOW-risk and within autonomous scope — execute directly."
**Impact:** Fixes root cause of autonomous channel failure for SKILL.md items. All future SKILL.md winners execute within 1 nightly cycle. 54 remaining god-class files will each need repair guidance — this makes the guidance self-delivering.
**Category:** workflow

---

### Idea 2: Re-Recommend post-split-test-repair SKILL.md — Human-Execute Framing
**Evidence:** Run 39 winner MISSING 2 nightly cycles. Content pre-written in `subconscious/runs/2026-05-29/winning-concept.md §Implementation Sketch`. Human present this session. 5-min execution. Autonomous channel confirmed broken for .md files.
**Action:** Human creates `.claude/skills/post-split-test-repair/SKILL.md` directly from content already written in run 39 winning-concept.md. Zero design work needed.
**Impact:** Unblocks email_sequences.py split (1255L, run 35 winner, ~2h). Prevents 4th repair commit. Pattern codified for 54 remaining god-class files.
**Category:** workflow

---

### Idea 3: Invoke /moratorium-sprint — 3 Items A+B+D (~40 min)
**Evidence:** Moratorium day 25+. Items A (check_project_invariants pre-commit), B (widget sync guard), D (CI eval workflow) all confirmed MISSING. moratorium-sprint SKILL.md exists (`7985fbb`). Human present in interactive session. Exit condition: pending ≤ 2.
**Action:** Human invokes `/moratorium-sprint` in this session.
**Impact:** Exits moratorium. Unlocks free-choice subconscious recommendations. Closes 3 items outstanding 25+ days.
**Category:** workflow

---

### Idea 4: PR #186 Dependabot Safe Merge
**Evidence:** @typescript-eslint/parser 8.58→8.60, 4 days old. Morning digest labels "Safe — merge now." Independent of moratorium. No code logic changes.
**Action:** Merge PR #186 via GitHub MCP.
**Impact:** Reduces PR noise. Safe minor version bump.
**Category:** operational

---

### Idea 5: Update god-class-refactor_plan.md — Mandatory Post-Split Test Repair Checklist
**Evidence:** 3 repair commits (5f2cd2b + 4afb3cf + bca2082) confirm 100% recurrence rate. `god-class-refactor_plan.md` lists 54 targets but no mention of test repair. Without codifying it in the plan itself, each of the 54 splits will generate a post-split repair commit.
**Action:** Add "Post-split test repair" as a mandatory checklist step in `god-class-refactor_plan.md` execution template. 4 commands (grep @patch, grep import, update paths, run pytest subset).
**Impact:** Ensures all 54 remaining splits include test repair regardless of whether SKILL.md exists. One-time plan edit (~10 min). Complementary to Idea 1.
**Category:** code_health
