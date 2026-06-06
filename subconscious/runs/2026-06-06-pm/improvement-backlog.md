# Improvement Backlog — 2026-06-06-pm (Run 52)

## Active

- **[Run 52 — AUTONOMOUS-EXECUTABLE]** Add post-fix re-scan to nightly-commit-review SKILL.md: after applying any LOW-risk fix, re-check `pending_autonomous` items for newly-unblocked pre-conditions and execute them. Also confirm run 50 Item B scope block is present.

## Parking Lot (survived debate but not chosen)

- **Merge PR #183 (billing fix, GH #181)** — 10 min human. Verify diff, merge. Closes GH #181, silences Check 11, unblocks email_sequences split. (Run 51 active_direction — bonus action until human executes.)
- **Tag GH #107 Zapier as ai-ready** — 2 min. Add `ai-ready` label + implementation hint comment. Routes to issue-to-pr-loop. Security gap, ROI 2.5.
- **email_sequences.py god-class split** — invoke `/god-class-splitter`. 1255L, 3 clean concerns. Prerequisites: GH #181 fix (to silence Check 11 noise) + ~2h human. (Run 41 active_direction.)
- **AI-to-Human Handoff v1** — Implementation sketch in `subconscious/runs/2026-05-28-pm/winning-concept.md`. Critical gap, 51 days. Agent OS merged. Governance: do not propose as winner until moratorium exits.
- **Zapier plan_status security fix** — GH #107, 37 days. Parking lot ROI 2.5. Route via issue-to-pr-loop after `ai-ready` label added.

## Rejected This Run

- **Merge PR #183 as winner** — WEAKENED. Run 51's active_direction, no new framing, human commitment bottleneck unchanged. Better as bonus action.
- **Tag GH #107 as winner** — WEAKENED. Parking lot note says "route via issue-to-pr-loop, not subconscious queue." Too small for winner slot during moratorium. Bonus action.

## Questions for Next Run

1. Did nightly 2026-06-06 (2:37 AM) apply run 52 winner (SKILL.md post-fix re-scan) AND cascade-wire Item A (Check 10)?
2. Was run 50 Item B scope block already present in the SKILL.md? Did Item B (check-widget-sync.sh) execute?
3. Was PR #183 merged by human? Is GH #181 closed?
4. Is moratorium exit condition (pending ≤ 2) now reachable? What's the true pending count after tonight's autonomous actions?
