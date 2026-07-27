# Run 106 Debate Log — 2026-07-27-pm

**Debating top 3:** Idea 1 (god-class-splitter Step 7), Idea 2 (feature-docs-trio skill), Idea 3 (feature-build docs seed)

---

## Round 1: Challenge

### Idea 1: god-class-splitter Step 7 — "No re-export shims" contradiction

**Challenger:** "Step 7 says 'No re-export shims' for a reason — if you keep re-exports, callers never update their imports. The whole point of a god-class split is to force callers to adopt the new module layout. Re-exports are a crutch that enables lazy callers."

**Defense:** "Both recent splits (calls.py + email_sequences.py) kept re-exports and STILL updated all explicit call sites. The re-exports are a safety net for callers missed in Step 6, not a replacement for Step 6. Without them, one missed importer causes a 500 at runtime. The skill-discovery evidence is unambiguous: 2 consecutive splits, 2 consecutive test-failure repair commits, same root cause. The current guidance is wrong — not aspirationally wrong, actively wrong."

**Evidence check:** `docs/skill-discovery/2026-07-27.md:133`: "Both omissions cause test failures immediately after the split." This is direct post-split evidence, not speculation.

**Verdict: SURVIVES.** The challenge relies on a theoretical argument against evidence-backed practice. Both splits this week required re-exports. Current guidance contradicts this. Fix is a 2-sentence SKILL.md edit with no downside.

---

### Idea 2: feature-docs-trio skill — invoke gap

**Challenger:** "3 occurrences in 7 days is strong evidence. But who runs this skill? If it only triggers when engineers remember to invoke it manually, the invoke gap kills the ROI. Skills that aren't auto-triggered save nothing."

**Defense:** "Skill-discovery explicitly acknowledges this: 'Add to feature-build/SKILL.md a Documentation step pointing to the feature-docs-trio skill.' The path is: create feature-docs-trio → reference from feature-build → engineers discover it organically. First step is creating the skill file."

**Second challenge:** "But feature-docs-trio doesn't exist yet. You can't reference a skill that doesn't exist. The feature-build SKILL.md pointer would point to a 404. And creating feature-docs-trio in this run is S-effort — more work than Idea 1's XS fix."

**Response:** "Fair. The correct sequence is (a) create feature-docs-trio, (b) add reference in feature-build. Both fit in one run but S-effort total. Compare against Idea 1's XS fix that prevents immediate, confirmed test failures."

**Verdict: WEAKENED.** S-effort vs XS. Invoke gap is real. Bootstrapping order requires both steps. Idea 1 outranks by effort and urgency.

---

### Idea 3: feature-build docs step seed — dependency on Idea 2

**Challenger:** "This is literally Idea 2 Step 2 without Idea 2 Step 1. Pointing feature-build to feature-docs-trio before creating feature-docs-trio is a broken reference."

**Defense:** "Could reference the pattern by description ('follow the KB article + ADR + runbook pattern') without naming a specific skill file."

**Challenge:** "Vague references in SKILL.md are useless. 'Follow the pattern' without a pointer to where the pattern is documented helps nobody. The reference has value only once feature-docs-trio exists."

**Verdict: KILLED.** Dependency on Idea 2 which itself is WEAKENED. No standalone value.

---

## Round 2: Winner Selection

| Idea | Status after Round 1 |
|------|---------------------|
| 1 | SURVIVES — XS, HIGH evidence, direct test failure prevention, immediate |
| 2 | WEAKENED — S-effort, invoke gap, bootstrapping dependency |
| 3 | KILLED — depends on Idea 2 |

**Winner: Idea 1** — Update god-class-splitter SKILL.md Step 7.

**Carry-forward tracking:**
- feature-docs-trio: 1st appearance as parking lot candidate. Promote at run 107 if still unimplemented.

---

## Implementation path

**Direct SKILL.md edit in this run.** Rationale:
- Nightly-commit-review channel cannot implement edits to non-nightly SKILL.md files — confirmed by all prior evidence
- Human won't manually edit a SKILL.md based on a winning-concept.md recommendation without a specific instruction
- The fix is XS (2-3 line edit to Step 7)
- Zero risk: SKILL.md is pseudocode guidance, not executable code
- Precedent: runs 99, 102, 104 all directly implemented SKILL.md edits
