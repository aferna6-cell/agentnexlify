# Idea 1: Step 9K — Stale Subconscious Draft PR Audit

**Evidence:** grep 'Step 9K' .claude/skills/nightly-commit-review/SKILL.md returns 0. Run 113 mandate: "if >=3 open subconscious PRs, Step 9K is run 113 winner." Condition confirmed: 23 run directories, governance tracked 5+ open subconscious PRs since run 102. Nightly-2026-08-31 confirms Step 9K absent (log search shows no Step 9K line). 1st carry-forward fires per autonomous-executable governance precedent (Steps 9F/9G/9I all implemented at 3rd or 1st carry-forward).

**Action:** Add Step 9K block to .claude/skills/nightly-commit-review/SKILL.md after Step 9J: list open PRs with head.ref starting "subconscious/", compute age_days, warn at stale_count≥3 (>30d), escalate comment on oldest PR at stale_count≥5 or critical_count≥1 (>60d). Summary line: "Step 9K: {N} subconscious PRs open ({S} stale, {C} critical)".

**Impact:** Prevents indefinite unmerged PR accumulation. Each nightly thereafter audits the subconscious backlog automatically — compounds forever.

**Category:** workflow_efficiency
