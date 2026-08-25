# Debate Log — Subconscious Run 2026-08-22-pm (#109)

Top 3 ideas ranked by impact: Idea 1 (Step 9J mandate), Idea 3 (GH issue middleware fix), Idea 2 (Step 9K PR closer).

---

## Idea 1: Step 9J — Dependabot Auto-Merge (carry-forward mandate)

### Challenge Round

**C1 — Evidence strength:** Is "6 PRs aging" strong enough to justify automated merging? Some Dependabot PRs touch breaking changes that CI doesn't catch.

**C2 — Highest leverage:** With GH #399 stalling 30 ai-ready issues and GH #669 exposing 97 router gaps, isn't security coverage more urgent than dep hygiene?

**C3 — What could go wrong:** A Dependabot PR bumps a dependency that has a breaking API change not caught by existing tests. Auto-merge ships a production regression.

**C4 — Previously rejected?** Not rejected. Step 9J has been the pending_approval winner since run 108. Governance explicitly set it as autonomous-executable at run 109.

**C5 — Too similar to active direction?** No — active_directions[0] IS Step 9J. This IS the active direction.

### Defense Round

**D1:** Evidence conclusive: 4 consecutive morning digests (2026-08-11/12/17/18) all flagged these exact PRs as "safe to merge." The heuristic (CI green + no review requests + no blocking labels) matches exactly what a human does when manually merging. Risk is not higher than manual; it's equivalent. Step 9J adds the same check a human would apply.

**D2:** Step 9J addresses the systemic operational gap. GH #669 is a security gap but requires M-effort human implementation (it's explicitly "human-approval required" in parking lot). Step 9J is XS effort, autonomous-executable, and closes a 4-week backlog immediately. Both problems can coexist; Step 9J doesn't block GH #669.

**D3:** Merge criteria protect against this: `mergeable_state=clean` means GitHub's merge check passed (no conflicts, CI green). For a Dependabot PR to have a non-obvious breaking change that CI doesn't catch, existing tests would need to be incomplete. If tests don't cover the changed API, the gap is in test coverage, not in Step 9J logic. The skip conditions (review requests, blocking labels) provide human override levers.

**D4:** Mandate is binding. Run 108 governance: "Autonomous-executable if not approved by run 109 (1st carry-forward mandate)." Run 109 = this run. Channel proven: Steps 9C/9E/9F/9G/9I all implemented via same channel, each within 1-2 cycles. This has the strongest governance mandate of any idea considered today.

### Verdict: **SURVIVES → WINNER**

Mandate fires. Evidence conclusive. Channel proven. Risk equivalent to manual merge. No new blocking evidence discovered.

---

## Idea 3: File GH Issue for Middleware-Level block_demo_role FastAPI Guard

### Challenge Round

**C1 — Evidence strength:** GH #669 (97 routers) was filed 2 days ago. The Step 9I nightly sweep will detect future regressions permanently. Is the middleware fix needed now when Step 9I is already guarding the class?

**C2 — Highest leverage:** A GH issue without a PR doesn't fix the 97 routers. GH #399 stalls the issue-to-pr-loop. Who implements this?

**C3 — What could go wrong:** A global FastAPI middleware that blocks demo_role on all routes could accidentally block admin routes, webhook routes, or test endpoints. The exclusion list could be wrong.

**C4 — Previously tried:** Run 108 parking lot explicitly labeled this "human-approval required." Filing an issue without approval changes nothing structurally.

**C5 — Redundancy:** GH #669 already tracks this. Adding another issue duplicates the tracker.

### Defense Round

**D1:** Step 9I guards FUTURE regressions but doesn't fix existing 97 missing guards. The middleware approach would retire Step 9I's remediation leg entirely. The issue would contain a precise implementation sketch, reducing implementation friction when GH #399 is resolved.

**D2:** Filing a GH issue with ai-ready label queues this for the issue-to-pr-loop when GH #399 is resolved. This is the standard flow for all structural fixes.

**D3:** The exclusion list is well-understood (auth.py, webhooks, admin/, widget routes). Previous GH #643 + GH #661 work documented exact patterns. Risk is bounded.

**D4:** Run 108 labeled middleware "human-approval required" meaning a full implementation needs human sign-off, not that a GH issue needs sign-off. Filing the issue is autonomous-executable.

### Verdict: **WEAKENED → Parking Lot**

Valid idea. But: GH #669 already tracks the underlying problem. Adding a second issue risks confusing the signal. The better path is to add an implementation sketch AS A COMMENT on existing GH #669, not a new issue. Promoted to parking lot: "Add middleware implementation sketch to GH #669 (not new issue)." This run's bandwidth goes to Step 9J mandate.

---

## Idea 2: Step 9K — Stale Subconscious PR Auto-Closer

### Challenge Round

**C1 — Evidence strength:** Are stale subconscious draft PRs actually a problem right now? The PR dedup guard prevents new ones. The run 108 parking lot listed this as "run 109+ candidate," not "run 109 winner."

**C2 — Highest leverage:** Step 9J is the mandate. Step 9K is a nice-to-have cleanup. With Step 9J the winner, Step 9K as a bonus action would expand scope past the single-winner rule.

**C3 — What could go wrong:** Closing a draft PR that a human intended to review could lose that branch's history from the PR view, creating confusion.

**C4 — Is count known?** The current open subconscious PR count isn't verified in this run's evidence.

**C5 — Premature?** The PR dedup guard (SKILL.md) already ensures only ONE open subconscious PR at any time going forward. Old pre-dedup-guard drafts are a historical artifact; they don't compound.

### Defense Round

**D1:** Even if they don't compound, stale draft PRs make the PR queue noisy for the human reviewer. A clean queue is hygiene.

**D2:** Step 9K is a valid addition AFTER Step 9J lands. Parking lot is the right place.

**D3:** Risk is bounded by the "no unmerged commits beyond main" guard. PRs with unique work survive; pure documentation drafts get closed.

### Verdict: **WEAKENED → Parking Lot (run 110 candidate)**

Strong mechanics, low urgency while PR dedup guard is active. Promote to run 110 if >3 stale subconscious PRs confirmed open.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Step 9J Dependabot auto-merge (mandate) | SURVIVES | **WINNER** |
| Middleware block_demo_role GH issue | WEAKENED | Parking lot (comment on GH #669) |
| Step 9K stale PR closer | WEAKENED | Parking lot (run 110 candidate) |
