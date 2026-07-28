# Debate — Idea 2: Step 9G CORRECTION (CCR Routine Monitor)

## FOR

**Mandated carry-forward, but original design is wrong.** Run 101 mandate item 1 says "Step 9G in SKILL.md?" — Step 9G is absent. Normal protocol: carry forward. But implementing the original Step 9G would create false alarms (`gh workflow run kb-autopopulate.yml` fails because GH Actions #500 is broken, then the nightly comments on #403 "Check ANTHROPIC_API_KEY" which is incorrect diagnostic — the CCR Routine handles this now, not GH Actions secrets).

**The corrected Step 9G addresses a real gap.** The CCR Routine was deployed 2026-07-23 and runs "twice daily" — but the KB log shows 5 days since last update. Two possible explanations: (a) CCR creates PRs that need merging, so log isn't updated by PRs — plausible; (b) CCR Routine has silently stopped. We cannot distinguish these from the nightly. That's a monitoring gap. The corrected Step 9G fills it.

**Same channel, proven pattern.** Step 9F (run 99 winner, implemented) is a working SKILL.md bash block that checks KB staleness and comments on GH. Step 9G corrected uses the same structure — `gh pr list` instead of `gh workflow run`, same comment pattern.

**Governance hygiene.** Marking original Step 9G as obsolete and updating the governance.json creates a clean audit trail. Future subconscious runs won't keep triggering carry-forward on a dead recommendation.

## AGAINST

**Challenge 1: The monitoring gap may not be a gap.** CCR creates PRs — checking `knowledge-base/log.md` for staleness is the wrong signal when the CCR path doesn't write to log.md. The "5 days since last update" could be normal if the CCR is creating PRs that haven't been merged yet. The corrected Step 9G would check for recent KB PRs — but what if the owner hasn't merged them? We'd get false positives: "CCR Routine may be stalled" when it's actually creating PRs waiting for review.

*Defense:* Real. This is a design flaw. The PR check needs to look at PRs created by the CCR (opened by claude.ai account), not merged PRs. If PRs exist but aren't merged, that's still actionable information — unmerged KB PRs piling up is a different problem. The alert can distinguish: "0 PRs in 48h: CCR stalled" vs "N PRs open, unmerged: owner review needed."

**Challenge 2: Is monitoring the CCR Routine the highest value use of the nightly bash block?** The nightly already monitors KB staleness (Step 9F). Adding Step 9G to monitor whether the thing monitoring KB staleness is working is meta-monitoring with diminishing returns. We could instead spend the bash block on something with direct customer impact.

*Defense:* This is the core tension. Step 9G fills an architectural gap (CCR Routine = new black box with no observability). But the corrected Step 9G is inherently reactive — it fires AFTER the CCR fails (48h+ no PR). The silent-green tenant heartbeat (Idea 3) is also reactive but with higher customer stakes.

**Challenge 3: Complexity of the corrected design.** The original Step 9G was ~30 bash lines (`gh workflow run`, sleep 30, check conclusion). The corrected Step 9G requires: `gh pr list --search "kb autopopulate"`, parse JSON, compare timestamps, conditional alert with correct diagnostic language. Higher implementation complexity, higher risk of bash bugs.

*Defense:* True, but all subconscious bash implementations have this risk. Step 9F itself is non-trivial. The pattern is proven.

## Verdict

MEDIUM candidate. The governance hygiene argument is compelling — marking original Step 9G obsolete is necessary regardless of what the run 101 winner is. The monitoring gap is real but the corrected implementation is more complex than a typical SKILL.md block and prone to false positives.

**Key insight:** The governance update (marking Step 9G obsolete) can and should happen regardless of winner. The monitoring improvement doesn't need to be the winner to get the governance correction.

Evidence score: 7/10. Execution risk: 5/10. Customer impact: 4/10. Governance impact: 9/10.
