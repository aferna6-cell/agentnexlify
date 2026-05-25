# Debate Log — Run 2026-05-25-pm (Run 33)

Top 3 ideas ranked by impact. Each gets 3-round challenge-and-defend.

---

## Idea 1: Create `god-class-splitter` Skill

**Initial rank:** #1 by impact (long-tail value, execution-layer, autonomous implementation possible)

### Round 1

**Challenge:** We already have `improve-architecture`, `tech-debt`, `dead-code-sweep`, and `plans/god-class-refactor_plan.md`. Another skill about god classes is documentation sprawl, not leverage.

**Defend:** Skill discovery 2026-05-25 explicitly mapped each existing tool: `improve-architecture` = diagnosis only, `tech-debt` = ranking/planning, `dead-code-sweep` = removal. None of them say "extract this concern, update these importers, run these checks." PR #180 (5-file split) required `5f2cd2b` (21 stale @patch repairs) and `4afb3cf` (1 stale import fix) as follow-up commits. A skill with the 12-step checklist prevents both. The split plan (`god-class-refactor_plan.md`) exists but doesn't execute — the skill is the execution arm.

### Round 2

**Challenge:** Only 2 distinct splits happened this week (local_seo + PR #180). Two occurrences might not justify a new skill — the skill-creator criteria says "recurring pattern."

**Defend:** Three occurrences per skill discovery (3555645 for local_seo + 2174732 for 5-file PR #180 + follow-up commits as distinct workflow instances). The plan doc lists 29 backend + 25 frontend files still exceeding 600 lines — this will recur weekly for months. Moratorium-sprint SKILL.md was created after similar evidence and was autonomously implemented by nightly review within 24 hours of recommendation (7985fbb).

### Round 3

**Challenge:** Creating the skill doesn't do the splits. If the bottleneck is human time for the actual refactors, the skill reduces context-loading but doesn't change the throughput.

**Defend:** Two effects beyond context reduction: (1) prevents follow-up test-repair commits by encoding step 10 ("verify no stale importers") in the checklist — currently skipped every time; (2) nightly review has demonstrated it can autonomously create skill files from subconscious recommendations (7985fbb moratorium-sprint, 2ce31b2 escalation protocol). This skill is a LOW-risk additive file creation — nightly review's wheelhouse. Once created, it reduces per-split friction for every future split. The ROI compounds across 54 remaining files.

**Verdict: SURVIVES** — strong recurrence signal, autonomous implementation possible, fills genuine gap between diagnosis (improve-architecture) and execution (nothing). Winner candidate.

---

## Idea 2: Fix GH #181 — AMOUNT_TO_PLAN Billing Gap

**Initial rank:** #2 by urgency (revenue impact, S-effort, CI trap active)

### Round 1

**Challenge:** This is the 3rd consecutive subconscious recommendation (runs 31, 32, 33). History shows when ideas are recommended 3+ consecutive times without implementation, the bottleneck is commitment/friction, not information. Repeating it doesn't change the bottleneck.

**Defend:** GH #181 differs from /moratorium-sprint in one critical dimension: the fix is ~15 min with exact line numbers, vs the moratorium sprint which was 40+ min of multi-file work. The repeat recommendations have each added new evidence (run 31: CI trap wired; run 32: failed second billing commit 1eaaeec). Run 33 adds: skill discovery confirms this as a documented billing bug class, and PR #180 landed without fixing it — confirming the gap persisted through the biggest dev activity in weeks.

### Round 2

**Challenge:** The real fix might not be this specific dict change — it might be ensuring Stripe webhook payloads include `metadata.plan`. If tenants set metadata.plan correctly, AMOUNT_TO_PLAN amount-fallback is never hit. Patching the fallback dict is treating the symptom.

**Defend:** `_resolve_plan` logic (billing.py:294-310) falls through to amount-based lookup when `metadata.plan` is absent OR when `plan` is not in the valid set. Stripe subscription renewal webhooks don't always include metadata from the original checkout. The AMOUNT_TO_PLAN dict is a documented resilience mechanism, not optional. CLAUDE.md explicitly lists $150 and $250 as current plan prices that must be in this mapping. Treating the dict as "unnecessary" contradicts the architectural decision already made.

### Round 3

**Challenge:** Even if implemented, the billing-constant-guard skill (Idea 3) addresses the root cause. Without the skill, a 4th billing commit could make the same mistake. Fixing GH #181 without creating the guard just resets the clock.

**Defend:** Both can coexist. GH #181 fix is the immediate tactical action (closes the gap today). The billing-constant-guard skill is the preventive systematic action (prevents recurrence). The fix should be recommended independently of the skill. The governance concern about 3+ consecutive recommendations is real — run 34 would trigger a governance switch if not implemented.

**Verdict: SURVIVES** — still the most urgent code health gap with direct revenue impact. Third consecutive recommendation but with genuine new evidence each run. GH #181 recommended with explicit run 34 escalation signal: if still not implemented by run 34, governance mandate fires (4-consecutive-run threshold).

---

## Idea 3: Create `billing-constant-guard` Skill

**Initial rank:** #3 by impact (root cause fix, but narrower scope than Idea 1)

### Round 1

**Challenge:** GH #181 is the symptom of a one-time drift between CLAUDE.md prices and billing.py. After GH #181 is fixed, billing constants won't need changing again for months or years. A skill for this is premature.

**Defend:** Skill discovery cited the TRIPLE-FIX pattern as recurring evidence — same pattern across 3 commits + 3 subconscious runs in 7 days. The structural risk persists: CLAUDE.md plan prices and billing.py AMOUNT_TO_PLAN are maintained separately. Any future pricing change (new plan tier, price adjustment) will create a new instance of this bug class. The "check for inverted tests" step — skipped twice — is non-obvious and exactly what a skill checklist encodes.

### Round 2

**Challenge:** The billing-constant-guard skill is essentially a sub-workflow of fixing billing bugs, not a standalone recurring skill. It would be invoked maybe once a year on pricing changes.

**Defend:** Skill discovery estimated 30-45 min wasted per occurrence. Even at once-per-year, the ROI over 3 years is 90-135 min saved + one prevented production billing regression. The "check for inverted tests" step saves a CI debugging session alone. The skill also adds value at code review time: when someone touches billing.py, the trigger fires and the checklist runs preventively.

### Round 3

**Challenge:** Creating this skill during an active moratorium (8 pending items) adds to the backlog. Run 33 should either clear pending items or not add new tools.

**Defend:** Skill files are LOW-risk additive (nightly review can create them autonomously). They don't add to pending_approval count since they're not code changes. However, Idea 1 (god-class-splitter) addresses a broader, higher-frequency gap. If only one skill can be created, god-class-splitter wins on recurrence frequency (weekly vs yearly) and long-tail value (54 remaining files vs 1 pricing change).

**Verdict: WEAKENED → Parking lot** — addresses real root cause but narrower scope than god-class-splitter. Promote to winner after GH #181 is fixed and god-class-splitter is implemented. Add to parking lot with promotion note.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| god-class-splitter skill | SURVIVES → WINNER | Create .claude/skills/god-class-splitter/SKILL.md |
| Fix GH #181 AMOUNT_TO_PLAN | SURVIVES → runner-up | Still most urgent human action; run 34 escalation if not done |
| billing-constant-guard skill | WEAKENED → Parking lot | Promote after GH #181 fixed |
| post-split-test-repair skill | Not debated (sub-step candidate) | Considered as Step 11.5 of god-class-splitter |
| improve-architecture handoff | Not debated | Bonus step after god-class-splitter exists |
