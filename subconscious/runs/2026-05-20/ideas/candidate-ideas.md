# Candidate Ideas — Run 26 (2026-05-20)

## Evidence Summary

**New since run 25 (2026-05-19):**
- Nightly review 2026-05-20 (commit 2ce31b2) autonomously implemented Item C from the moratorium sprint: added `## Moratorium Escalation Protocol` section to `.claude/skills/nightly-commit-review/SKILL.md`. Second autonomous implementation in 2 days (after 7985fbb created moratorium-sprint SKILL.md on 2026-05-19).
- Sprint now has 3 remaining items (A, B, D) not 4 — estimated ~40 min, not ~50 min.
- Zero production feature commits — day 15. Moratorium still active.
- Pending items: governance says 10; Item C (run 19) now autonomously implemented → effective pending = 9.
- `scripts/check-widget-sync.sh` MISSING (confirmed). `.github/workflows/lead-qualifier-eval.yml` MISSING (confirmed). `check_project_invariants.py` NOT in pre-commit (confirmed — only Check 9 in hook).

**Pattern:** The autonomous loop (nightly review) is now implementing subconscious winners without explicit human instruction, on consecutive days. Items C and the moratorium-sprint SKILL.md were both done this way.

---

### Idea 1: Invoke /moratorium-sprint — 3 Items Remain After Item C Completed Today

**Evidence:** Item C (Moratorium Escalation Protocol in SKILL.md) implemented autonomously by nightly review today (2ce31b2). Sprint reduced from 4 items to 3. Items A (check_project_invariants pre-commit, ~5 min), B (widget sync guard, ~15 min), D (CI eval workflow, ~20 min) still missing, verified via direct file checks. moratorium-sprint SKILL.md exists (7985fbb). Sprint load = ~40 min. Run 25 governance condition: "If not invoked by run 26, escalate to nightly-commit-review as automatic trigger."

**Action:** Human invokes `/moratorium-sprint` in this or any interactive session. Skill reads governance.json, skips Item C (already done), executes A→B→D, opens draft PR.

**Impact:** 3 items committed, draft PR opens, pending 9→6 when merged. Moratorium exit path begins. After 4 more governance resolutions (runs 20/21/22 GH actions), pending ≤ 2 → moratorium exits.

**Category:** workflow

---

### Idea 2: Authorize Nightly Review to Autonomously Execute Items A + B

**Evidence:** Nightly review has now autonomously implemented 2 subconscious winners in consecutive days (7985fbb + 2ce31b2) without explicit instructions — both were skill-file modifications classified as LOW-risk. Items A (3-line pre-commit addition) and B (new bash script creation) are similarly scoped. The autonomous pattern is established and working.

**Action:** Update `.claude/skills/nightly-commit-review/SKILL.md` to explicitly include Items A and B in its LOW-risk autonomous execution scope. Add a check: if `moratorium_active: true` AND item implementation sketch exists AND item is file-creation/pre-commit-addition (not GitHub workflow), execute autonomously.

**Impact:** Items A and B done within 24 hours without human action. Only Item D (GitHub Actions workflow, more complex) requires human. Sprint PR can open after D.

**Category:** workflow / operational

---

### Idea 3: Create pre-commit-guard-add Skill (.claude/skills/pre-commit-guard-add/SKILL.md)

**Evidence:** Skill discovery 2026-05-18 ranked this #2 after moratorium-sprint (which is now created). Every new bug class requires the same 8-step process: read hook for current Check N → determine insertion point → write check block → add opt-out escape hatch → test positive case → test negative case → update CLAUDE.md → commit. Pattern derived each session. Cadence: ~1-2 guards/month. Saves 15-20 min per guard. Check 10 (check_project_invariants) is the perfect seed case — fully pre-written in run 22 sketch.

**Action:** Create `.claude/skills/pre-commit-guard-add/SKILL.md` with the 8-step process, using 72f8204 (Check 9) as the canonical example and run 22 sketch as the Check 10 seed.

**Impact:** Future bug guards take 15-20 min less per occurrence. ~1-2/month = 15-40 min/month compounding. Nightly review could also use the skill to add guards autonomously.

**Category:** workflow

---

### Idea 4: Merge 4 Aging Safe Dep PRs (#102, #103, #163, #164)

**Evidence:** PRs #102 (youtube-transcript-api ≥1.2.4) and #103 (python-multipart 0.0.26→0.0.27) are 21+ days old. PRs #163 (@typescript-eslint/parser 8.58→8.59.3) and #164 (@playwright/test 1.59.1→1.60.0) are 8 days old. All are patch-level or minor upgrades. Independent of moratorium. No production code changes. Listed as "bonus" in runs 24-25 but never explicitly recommended.

**Action:** Use `mcp__github__merge_pull_request` on each of the 4 PRs. ~5 min total.

**Impact:** Reduces dependency drift. Minor security/compat improvements. Cleans pending PR queue before sprint PR opens.

**Category:** operational

---

### Idea 5: Wire check_project_invariants.py Into Pre-commit as Standalone Fix (Item A Only)

**Evidence:** Run 8 winner (25 days stale). Only 3 lines to add to scripts/hooks/pre-commit after Check 9 (line 225). Script passes all 6 checks (no blockers since 8f680e8). This is Item A from the sprint — could be done independently without invoking the full /moratorium-sprint skill.

**Action:** Edit `scripts/hooks/pre-commit` to add 3-line call to `python3 scripts/check_project_invariants.py` as Check 10. Commit: `chore: add Check 10 — wire check_project_invariants into pre-commit`.

**Impact:** Naming violations (client_id, status, areas_of_interest) blocked at commit time. Costs 5 min. Reduces pending from 9 to 8.

**Category:** code_health
