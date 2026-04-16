# Debate 3: Migration Safety Net — Pre-Push Unapplied Migration Check

## Steel-Man

Schema drift from unapplied migrations has been the root cause of 2 out of the last 5 major bugs, and currently 3 P0/P1 tasks on the board are just "apply pending migrations." A lightweight check that blocks (or warns on) pushes that leave migrations unapplied for > 24 hours costs 0.5–1 day of implementation and permanently changes the risk profile of schema changes. This is a systemic fix, not a one-off patch.

## Hard Objections

**Objection 1: The check can't run without a live Supabase connection. Pre-push hooks that need network access are fragile — timeout in CI/CD, fail in offline dev, introduce a new external dependency into the dev loop.**

A flaky pre-push hook is worse than no hook. Developers will add `--no-verify` to bypass it, which defeats the purpose and degrades hook discipline.

*Rebuttal:* The hook can be designed to warn-only (exit 0) on network timeout — it never blocks a push due to connectivity. It only blocks when the check succeeds AND finds stale migrations. A failed network connection is logged as "could not verify, proceeding" not as a blocker. The CI/CD version (GitHub Action) runs in a controlled environment where network is reliable.

**Objection 2: The real problem is process discipline, not tooling. Developers already know migrations must be applied. Adding a hook doesn't fix the underlying reason they're delayed (complex multi-step apply process, waiting for MCP tool, etc.).**

If migrations are delayed because applying them is hard, a check that highlights the problem doesn't make applying them easier — it just adds friction to pushes.

*Rebuttal:* This objection is partially valid. The migration-apply process is documented as requiring Supabase MCP or the SQL editor — neither is a one-command operation. The safety net's value isn't in eliminating the delay; it's in making the delay explicit and tracked. Currently, "migrations pending" is discoverable only by reading daily logs. A hook makes it visible at the moment of push, which is the right time to notice.

**Objection 3: This is already tracked in the morning routine health checks and daily logs. We have visibility. The problem is prioritization, not detection.**

If the daily logs have said "apply migrations 065–070" for 11 days with no action, the signal is already there and being ignored. A new hook won't change behavior.

*Rebuttal:* This objection is strong. It suggests the problem is decision-making, not tooling. The 11-day-old migrations are known; the bottleneck is human action. A hook changes the channel (at push time vs. in a morning report) but doesn't change the priority calculus. This is a weaker systemic fix than it initially appears.

## Verdict

**De-prioritize.** The strong objection #3 is correct: visibility is not the bottleneck. The bottleneck is prioritization and the friction in applying migrations (Supabase MCP dependency). The migration check tool still has value but is a lower-priority systemic improvement than AI handoff. It should be added as a follow-up task after the apply process itself is streamlined (e.g., a `scripts/apply-migration.sh` helper).

**Final verdict: VALID but OUTRANKED. Not the winner in this cycle. Add to improvement backlog for a future cycle after the apply-friction problem is addressed.**
