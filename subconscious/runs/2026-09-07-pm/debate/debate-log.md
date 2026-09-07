# Debate Log — Run 118 (2026-09-07-pm)

Debating top 3 ideas by expected impact.

---

## Idea 1: Create `meter-ai-endpoint` Skill

### Challenge

**Is the evidence strong enough?**
9 commits in one week is high signal. But the metering retrofit sprint (#792–#799) was triggered by a specific PR audit — not a recurring habit. Could this week be an anomaly?

**Is this the highest-leverage thing right now?**
Step 9L is now live. Every nightly will surface unmetered endpoints automatically. The deficit closes without a skill. Does the skill add marginal value on top of Step 9L?

**What could go wrong?**
A skill with a 6-step checklist risks becoming stale if import patterns or the metering lifecycle change. Maintenance cost for a skill that is already partially covered by the existing `ai-feature-pattern` skill.

**Similar rejected before?**
Not in governance's frozen_ideas or rejected_paths.

**Too similar to active direction?**
Active direction is Step 9L (detecting violations). This skill covers remediation. Complementary, not duplicative.

### Defend

**Anomaly?** No. The 9 commits retroactively metered 9 distinct functions across 5 files — this is a structural pattern, not a one-time audit. New AI routes will keep shipping. Step 9L detects the gap but does not tell developers what the fix pattern is. Skill bridges that gap.

**Marginal value over Step 9L?** Step 9L files a GH issue but gives developers a 7-word issue title with no implementation guidance. The skill gives the exact 6-step checklist: imports, helper function shape, 4 test cases, CI line. Without the skill, each fix is independently re-derived (wrong alias, missing release branch, missing CI append — all happened this week per commit diffs).

**Stale risk?** The `meter-ai-endpoint` skill references `check_ai_metering.py` as the authoritative source. If the metering lifecycle changes, both the skill and the detector update in one PR. Low maintenance cost.

### Verdict: SURVIVES

Strong evidence, fills an unaddressed remediation gap, no rejection precedent, low maintenance cost. 30–60 min saved per endpoint × recurring pattern.

---

## Idea 2: Update `ai-feature-pattern` SKILL.md to Cross-Reference Metering

### Challenge

**Is the evidence strong enough?**
Skill discovery proposed it as LOW priority. The `ai-feature-pattern` skill is invoked before an AI endpoint is built; metering is an afterthought that Step 9L catches. Is adding one cross-reference paragraph worth a subconscious winner slot?

**Highest leverage?**
If Idea 1 (meter-ai-endpoint skill) wins, the cross-reference in ai-feature-pattern becomes a 2-line pointer to that skill. The value is almost entirely captured by Idea 1 — this is a trailing improvement.

**Too similar to current active direction?**
Directly overlaps with Idea 1 — both address the metering gap. Idea 1 is the stronger version.

**Could go wrong?**
Nothing breaks. XS effort. But choosing this as winner over Idea 1 leaves the remediation checklist unwritten.

### Defend

Still worth doing. At the moment a developer invokes `ai-feature-pattern`, the skill says nothing about billing. Adding one sentence — "See `meter-ai-endpoint` skill after building your endpoint" — at the skill-invocation point catches the gap earliest.

### Verdict: WEAKENED

Real improvement but subsumed by Idea 1. Implement as a bonus action inside Idea 1 (add a cross-reference line to `ai-feature-pattern` while creating `meter-ai-endpoint`). Does not need to be the winner.

---

## Idea 3: os_tool_executions.py God Class Split

### Challenge

**Governance mandate condition not met:** mandate specifies "10d+ stable" for the god class split. f22ef04 was committed 2026-09-03 — only 4 days before today (2026-09-07). Governance's previous stability estimate was incorrect (runs 115–117 said "8d+ since f22ef04" but the commit date is 2026-09-03). Actual stability: 4 days.

**Evidence for urgency?**
File is 783L but was modified 4 days ago as part of Billing Automation v1. Active development means a split now risks a merge conflict or conceptual fragmentation of an in-progress effort.

**What could go wrong?**
Split on an actively-changing file = immediate merge conflict risk. If Billing Automation v2 or M9 features touch os_tool_executions.py next week, the split becomes a multi-file rebase exercise.

**Higher-leverage alternatives?**
Idea 1 prevents ongoing metering debt accumulation. Idea 3 reduces code complexity in one file. Metering debt has a direct revenue impact; code complexity does not.

### Defend

783L is legitimately above the 600L CLAUDE.md Rule 9 threshold. The split is correct eventually. The skill split candidate is sound in isolation.

But the mandate's precondition exists for a reason: wait for stability. 4 days is not stable enough for a multi-file refactor. Run 119 candidate if still 0 commits by then.

### Verdict: WEAKENED → Parking Lot

Correct eventual action, wrong timing. Stability condition not met. Defer to run 119.

---

## Synthesis

- **Idea 1 (meter-ai-endpoint skill): SURVIVES → WINNER**
- **Idea 2 (ai-feature-pattern update): WEAKENED → bonus action inside Idea 1**
- **Idea 3 (os_tool_executions split): WEAKENED → parking lot (run 119 candidate)**
- **Idea 4 (Step 9J budget fix): WEAKENED → needs diagnostic data first (parking lot)**
- **Idea 5 (staging-preflight skill): SURVIVES → parking lot (MEDIUM priority, no mandate)**
