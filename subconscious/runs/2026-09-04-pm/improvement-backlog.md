# Improvement Backlog — Run 115 (2026-09-04-pm)

## Active
- **Step 9L: Nightly AI usage metering coverage sweep** — grep backend/routers/ for Claude API calls lacking usage guard, file ai-ready issues per unguarded file. Autonomous-executable via SKILL.md-edit channel. Confidence: HIGH.

## Parking Lot (survived debate, not chosen)
- **Migration alerter: Unapplied migration alerter** — run check_schema_log_migrations.py in nightly, alert if schema-log/migration drift found. Blocked until PR #788 merges. Evidence: f72a274 shows manual schema-log updates bypassing PR flow. Unblock condition: PR #788 merged.
- **os_tool_executions.py god class split** — 783L file (30% over threshold). Borderline stable (3 days since last commit). Becomes run 116 candidate at 4+ days stable. Use god-class-splitter skill. Three clear split points: dispatch, approvals, action bridge.
- **Migration alerter via PR #782** — prior draft subconscious PR (2026-09-03) references this. Absorb into migration alerter parking lot entry above.

## Rejected This Run
- **Fix Step 9J merge eligibility deferral** — KILLED. CI dark (GH #500) since 2026-07-20 means auto-merging without CI confirmation is unsafe. Rebase trigger (@dependabot rebase on unknown-state PRs) remains the correct Step 9J posture. Revisit when CI re-enabled or when specific PRs are confirmed green via manual check.

## Questions for Next Run
1. Did Step 9L fire in the first nightly post-implementation? How many unguarded files found?
2. Has PR #788 (check_schema_log_migrations.py) been merged, unblocking the migration alerter?
3. Is os_tool_executions.py still stable (no commits for 4+ days)? If yes: god class split as run 116 candidate.
4. Has SUPABASE_ACCESS_TOKEN been set in Railway, unblocking brain connector (GH #684)?
5. Has GH #669 (class-wide block_demo_role middleware fix) received a PR from the issue-to-pr loop?
