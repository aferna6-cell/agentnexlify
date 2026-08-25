# Improvement Backlog — 2026-08-17-pm

## Active (run 107 mandate)
- **Step 9I: Add nightly demo-role security sweep** — Edit `.claude/skills/nightly-commit-review/SKILL.md` to add Step 9I block. See winning-concept.md for exact implementation sketch. Status: PENDING_HUMAN_APPROVAL. Escalates to autonomous-executable if not actioned by run 108.

## Bonus (can execute without approval)
- **GH #403 targeted comment** — Post exact steps to add ANTHROPIC_API_KEY to GitHub Actions secrets (Settings → Secrets and variables → Actions → New repository secret → ANTHROPIC_API_KEY → value from Railway). Unblocks 25-day KB staleness. Low risk, high value, one-time.

## Parking Lot (survived debate but not chosen)
- **dependabot-merge-runner SKILL.md** — 4 Dependabot PRs (#629, #630, #631, #649) at 7-14 days. Revisit when GH #399 (AUTOPILOT_GH_TOKEN) resolved and PR backlog grows past 10+.
- **GH #660 fix sketch comment** — Pre-load implementation sketch for scoring_config.py block_demo_role (4 routes). Useful when issue-to-pr-loop unblocked (GH #399). Low priority while loop is stalled.
- **stale-autonomy-pr-closer SKILL.md** — 6 draft subconscious PRs accumulating. Revisit at 10+ PRs or when oldest (#606) hits 30 days.
- **orphaned-commit-recovery SKILL.md** — From skill discovery 2026-08-17. Lower priority now that git push added to Phase 8 (run 105 win).

## Implemented This Run
- (none — this run produces only a recommendation)

## Carry-forwards Resolved This Run
- run_106_mandate item 6 (propose Step 9I): DONE — Step 9I proposed as winner
- run_106_mandate item 1 (verify git push in SKILL.md): PASS
- run_106_mandate item 2 (verify route-security-guard-audit SKILL.md in origin): PASS
- run_106_mandate items 3/5 (KB staleness, SUPABASE_ACCESS_TOKEN): still unresolved, escalated to run_107_mandate

## Questions for Next Run (run 107)
1. Has Step 9I been approved and implemented? If not, has it been 2 runs → escalate to autonomous-executable?
2. Did the GH #403 bonus comment unblock KB autopopulate? Check knowledge-base/log.md.
3. GH #661 (scoring_config.py): has a PR been filed yet? GH #399 still blocking?
4. SUPABASE_ACCESS_TOKEN: has human filled in last_rotated date in ops/credential-rotation-schedule.md?
5. Dependabot PRs (#629-631, #649): still open? Count grown past 10?
6. GH #394 (brain connector staleness): still open? Any progress?
