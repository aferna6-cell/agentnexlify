# Debate Log — Run 110 (2026-08-26-pm)

Top 3 ideas debated: Idea 1 (Step 9J fix), Idea 2 (block_demo_role middleware), Idea 4 (Step 9K).

---

## Idea 1: Fix Step 9J — Switch from `mergeable_state` to commit check-runs

### Challenge Round 1
**Attack:** `mergeable_state: "unknown"` is transient. GitHub computes it asynchronously. By the time nightly fires at 2:37 AM, most PRs should have resolved from `unknown` to `clean` or `dirty`. If the nightly ran at 2:37 AM and still saw `unknown` on 19 PRs, maybe CI just hadn't run yet or the PRs are conflicted.

**Defend:** These Dependabot PRs are 4+ weeks old (#629/#630/#631/#649 from runs 108/109). If `unknown` were transient and cleared in hours, 4-week-old PRs would show `clean` or `dirty` by now. GitHub's API documentation explicitly states `mergeable_state` is computed lazily and can revert to `unknown` after a period of inactivity. The correct pattern for CI-gated automated merging is to check the head commit's check-run conclusions directly — this is what the GitHub UI uses internally and what Dependabot auto-merge uses natively.

### Challenge Round 2
**Attack:** Switching to check-run queries is a more complex SKILL.md edit. Could introduce bugs — what if check run names differ across repos? What if a required check hasn't started yet?

**Defend:** The guard is already conservative: if no check runs exist (CI not triggered), skip with log. If any required check is not `conclusion: "success"`, skip. This is strictly safer than trusting `mergeable_state`. Complexity delta: 4 extra lines in the Step 9J block. Risk of false-positive merges is lower than current false-negative rate (100% false negatives = 0 merges).

### Challenge Round 3
**Attack:** Is this the highest-leverage action? The underlying issue is 19 PRs with `unknown` state — maybe the real fix is to trigger Dependabot's native auto-merge via GitHub settings rather than implementing our own.

**Defend:** GitHub Dependabot auto-merge requires a GitHub Actions workflow to be running, which is dark since 2026-07-20 (GH #500). Our nightly runs via Routines + MCP — the only automation path available. SKILL.md edit is the proven autonomous-executable channel (Steps 9C/9E/9F/9G/9I/9J all landed this way). One SKILL.md edit compounds indefinitely.

**Verdict: SURVIVES → chosen as winner.** Evidence is direct (nightly log confirms 0 merges on first execution). Fix is small, autonomous-executable, high-compounding impact. Passes all 3 challenge rounds.

---

## Idea 2: Add `block_demo_role` FastAPI middleware

### Challenge Round 1
**Attack:** This is M-effort human-approval work. The subconscious can only write into SKILL.md or make XS/S edits autonomously. What can the subconscious actually DO for this idea?

**Defend:** Subconscious can enrich GH #669 with a detailed implementation sketch — exact code for the middleware pattern, allowlist, test structure. This unlocks issue-to-pr-loop execution when GH #399 unblocks.

### Challenge Round 2
**Attack:** GH #669 already has a comment from the nightly mentioning the middleware approach. Adding another comment is marginal value. And issue-to-pr-loop is stalled (GH #399 Day 41+). This recommendation can't execute.

**Defend:** GH #669 may not have a full implementation sketch yet. But the constraint (GH #399 blockage) is real — even with a sketch, no automated PR will open until #399 is resolved.

### Challenge Round 3
**Attack:** Step 9I is doing the per-file patching. Is the class-wide middleware truly the right fix, or should we keep tracking per-router?

**Defend:** 97 routers is beyond per-file tracking. But human approval is required regardless.

**Verdict: WEAKENED → parking lot.** Good idea but not autonomous-executable in current state. GH #399 blocks execution path. Run 111 candidate when GH #399 resolves.

---

## Idea 4: Step 9K — Stale subconscious PR report in nightly

### Challenge Round 1
**Attack:** How many open subconscious PRs are there right now? If run #109 merged into existing PR #674, there may be very few. Step 9K solves a problem that may not currently exist at scale.

**Defend:** run_109_mandate explicitly named Step 9K. The governance pattern is: when a mandate names a step, and it passes the "autonomous-executable" bar, implement it. Historical peak was 5-6 open PRs. Even at 2-3, surfacing their status daily is better than silent drift.

### Challenge Round 2
**Attack:** Report-only steps add log noise without directly fixing anything. The nightly is already getting long with Steps 9A through 9J. Adding 9K extends it further without immediate user value.

**Defend:** Step 9K is report-only — no API calls beyond list_pull_requests, no comments posted unless PRs are stale. Marginal cost (1 list call). And the governance mandate explicitly requires it.

### Challenge Round 3
**Attack:** Compared to Idea 1 (fixing Step 9J to actually merge security patches), Step 9K is pure hygiene. Idea 1 has measurable security impact. Is Step 9K a better winner than Idea 1?

**Defend:** It's not — Idea 1 is higher leverage. Step 9K can be proposed as a bonus action this run.

**Verdict: WEAKENED → parking lot.** Lower leverage than Idea 1. Implement as a bonus action within this run, or carry forward to run 111 as a paired SKILL.md edit alongside the Step 9J fix block update.

---

## Summary

| Idea | Verdict | Notes |
|------|---------|-------|
| 1. Fix Step 9J check-runs gate | **SURVIVES → WINNER** | Autonomous-executable, S effort, direct security impact |
| 2. block_demo_role middleware | **WEAKENED → parking lot** | M-effort, GH #399 blocks execution path |
| 4. Step 9K stale PR report | **WEAKENED → parking lot** | Lower leverage; run 111 candidate or bonus |
| 3. Voice addon double-billing | Not debated (M-effort, run 111 candidate) |  |
| 5. churn_watch daily trigger | Not debated (needs endpoint verification first) |  |
