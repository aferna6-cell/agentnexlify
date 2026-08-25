# Improvement Backlog — Run 110 (2026-08-25)

## Active
- **Step 9K: Stale subconscious PR closer in nightly-commit-review SKILL.md** — auto-close superseded drafts (implemented=true guard), escalate 21d+ unapproved ones. Reduces PR queue from 4 to ≤2 on first run. Autonomous-executable SKILL.md edit.

## Parking Lot (survived debate but not chosen)

- **memory.jsonl dedup guard** (Idea 2) — run 109 wrote two identical entries. Fix: check last entry's run/winner before appending. XS effort. Pick when no higher-leverage item available. ROI low, correct direction.

- **Step 9J GH-Actions-dark fallback** (Idea 3) — when GH Actions dark, Step 9J logs "0 merged" with no diagnostic. Update Step 9J to detect dark state and post explicit "manual merge needed" guidance. S effort, honest logging improvement.

- **Step 9J dark-state awareness** (Idea 5) — detect `mergeable_state: unknown` as a GH-Actions-dark signal rather than a CI-failure signal. Prevents misleading logs. S effort.

- **Block_demo_role middleware in main.py** (Idea 4) — WEAKENED. PR #653 already has this proposal; re-recommending without autonomous execution path adds noise. Re-elevate when GH #399 resolved so issue-to-pr-loop can implement autonomously. ROI very high but blocked on human code review.

- **conversation_enrichment_job.py scheduling** (from run 98) — no .github/workflows/conversation-enrichment*.yml; job never runs. BLOCKED on GH #399.

- **Enable kb_hybrid_retrieval** (from run 98) — FTS+semantic merge behind feature flag. BLOCKED: no Settings UI for feature flags, GH #399 blocks ai-ready queue.

## Rejected This Run

None killed (only weakened to parking lot).

## Questions for Next Run

1. Did Step 9K auto-close PRs #575 and #626? If not, why (governance.json match criteria may need tuning)?
2. Has the owner addressed GH Actions dark state (#500)? If yes, Step 9G/9J will recover immediately.
3. Are Dependabot `mergeable_state: unknown` PRs now "clean" after 24-48h?
4. KB still 33d stale — is ANTHROPIC_API_KEY rotation blocked on something specific?
5. Is block_demo_role middleware (PR #653) ever going to get a human review, or should subconscious escalate differently?
