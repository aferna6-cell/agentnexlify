# Debate Log — 2026-08-01-pm (Run 101)

Top 3 ideas by impact × effort: Idea 1 (Step 9G), Idea 2 (prospecting.py split), Idea 3 (GH #399 comment).

---

## Idea 1: Step 9G — KB Self-Healing Trigger

### Challenge
- Run 100 picked the same winner and it wasn't implemented. Is this channel reliable for idea generation if it keeps being a carry-forward?
- The KB might fix itself soon — `kb-autopopulate.yml` could just run on schedule.
- Step 9F already alerts; is autonomous repair actually necessary vs. waiting for human action?

### Defend
- Channel IS reliable for SKILL.md bash blocks. Steps 9B/9C/9D/9E/9F all implemented in 1 nightly cycle each. The miss last run was because nightly had a clean window (no code commits to review). That's fixed: nightly is running daily now with active commits.
- KB at 9 days stale, same gap class that caused 63-day degradation in early 2026. Step 9F alerting alone didn't prevent the original 63-day gap.
- Autonomous repair is the difference between "human must notice a Slack-less GitHub comment" and "system self-heals within 24h." Given GH #403 has 0 human responses in 18+ days of Step 9F commenting, repair is clearly needed.
- `gh workflow run` is in the same permission scope as `gh issue comment` which nightly already uses successfully.

### Verdict: **SURVIVES → WINNER**

---

## Idea 2: prospecting.py God-Class Split

### Challenge
- prospecting.py is 536L, not 600L. CLAUDE.md Rule 9 says factor at 600L+, not before. This fires the rule prematurely.
- PR #619 landed 2 days ago. Splitting before production validates the design risks creating wrong module boundaries.
- /god-class-splitter requires an interactive human session (can't be autonomously executed by nightly). This makes it M-effort with low implementation probability.
- 3 other services from PR #619 (gmail_connector 518L, sms_agent 489L, escalations 415L) are at similar or greater risk — prospecting isn't uniquely the problem.

### Defend
- At 536L and rapidly growing (social_engagement.py, social_publisher.py, etc. all landing in same sprint), the 600L threshold will be crossed within 1-2 more feature additions.
- The test file (test_prospecting.py at 1368L) signals the module is already hard to test in isolation — that's a code smell independent of LOC count.
- early split when concerns are still cleanly separated is always cheaper than emergency split under production load.

### Verdict: **WEAKENED → parking lot**. Revisit at 600L or when a bug is traced to the mixed concerns.

---

## Idea 3: GH #399 Specific Rotation Steps Comment

### Challenge
- 7+ escalation comments have already been posted on GH #399 (runs 93–100 escalated repeatedly). Another comment likely gets the same zero-response treatment.
- The autonomous loop (d7259d4, 2026-07-26) may have made issue-to-pr-loop less critical — the new `backend/graph/` system might pick up ai-ready issues differently.
- This is operational busywork, not systemic improvement. The fix is a human action (token rotation), not something the subconscious can unlock.

### Defend
- Previous comments were diagnostic ("loop stalled N days"). None included the exact Railway navigation path. There is a difference between "here's the problem" and "here's the 3-step fix."
- The new `backend/graph/` autonomous loop is separate from `autopilot-issue-loop.yml` GitHub Actions — they handle different work classes. The issue-to-pr-loop still matters for the 3 open ai-ready issues.
- Specific rotation steps reduce human activation energy from ~20 minutes (investigate + find token page) to 3 minutes (copy-paste).

### Verdict: **WEAKENED → parking lot**. Step-by-step comment is valid but lower leverage than Step 9G's systemic repair. Can be added as a Bonus Action.

---

## Summary

| Idea | Verdict |
|------|---------|
| 1: Step 9G KB self-healing trigger | SURVIVES → **WINNER** |
| 2: prospecting.py god-class split | WEAKENED → parking lot |
| 3: GH #399 specific steps comment | WEAKENED → parking lot (Bonus Action) |
| 4: connector_registry.py ADR | Not debated (not top 3) → parking lot |
| 5: PWA push on appointment_completed | Not debated (not top 3) → parking lot |
