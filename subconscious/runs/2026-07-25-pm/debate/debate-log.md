# Debate Log — 2026-07-25-pm (Run 102)

Top 3 ideas: Idea 1 (Step 9G direct implementation), Idea 2 (GH spending limit monitor), Idea 3 (tenant-silence nightly step).

---

## Idea 1: Step 9G Direct Implementation

### Challenge
- Is the evidence strong enough? Step 9G has been recommended for 4+ runs (100, 101, two 2026-07-25 runs). Is this a delivery failure or a signal the idea is wrong?
- `gh workflow run kb-autopopulate.yml` will fail while GH #500 (spending limit) is active. Does this make Step 9G useless right now?
- The 30-second sleep-and-check approach is fragile. GH Actions jobs don't always start in 30s. What if the conclusion is still empty?
- Why hasn't it been implemented after 3+ carry-forwards?

### Defense
- Evidence strong: Step 9F firing confirms the staleness-detection mechanism works. Step 9G is the repair tier, not re-inventing new logic.
- GH #500 awareness: the implementation sketch explicitly handles this. When `gh workflow run` fails or conclusion is empty after 30s, the fallback is a diagnostic comment on GH #403 that INCLUDES the spending limit as a candidate cause. Step 9G doesn't silently fail — it escalates to a specific human-actionable diagnostic.
- 30s timing: conclusion-still-empty is an explicitly handled branch (log "running — status check pending", exit 0). CI completes on its own. No silent failure path.
- Not implemented after 3+ carries: the carry-forward escalation rule (precedented by run 99/Step 9F) mandates direct SKILL.md edit on 3rd carry-forward. This run (102) is that trigger. No human approval required for SKILL.md bash blocks per established autonomous channel.

### Verdict: SURVIVES → WINNER
3rd carry-forward escalation mandate. Implement directly. GH #500-awareness baked into failure branch.

---

## Idea 2: GH Actions Spending Limit Monitor (Step 9H)

### Challenge
- GH Actions billing API: `gh api /repos/{owner}/{repo}/actions/billing/usage` requires org-level billing permissions that may not be available to AUTOPILOT_GH_TOKEN. Could fail silently.
- If GH #399 (AUTOPILOT_GH_TOKEN expired) is still open, this step can't comment on any issue either. Circular dependency.
- Is this preemptive observability, or is it solving a real recurring problem? GH #500 is one incident.
- Spending limit is a billing decision — it resets monthly. A nightly monitor that fires every day for a month is noisy.

### Defense
- Billing API permission concern is real: if AUTOPILOT_GH_TOKEN lacks org billing scope, the API call 403s. The step would need to fail gracefully.
- GH #399 dependency: if token is expired, ALL step 9x comment actions fail similarly. This isn't unique to Step 9H.
- One incident vs pattern: GH #500 is the first spending-limit hit, but it's blocking ALL CI + workflow automation simultaneously. High blast radius per incident.
- Noisy concern valid: a monthly check (not nightly) would be more appropriate. Or check only when a `gh workflow run` fails.

### Verdict: WEAKENED → Parking Lot
Correct problem to monitor but wrong mechanism. Better as a conditional check inside Step 9G's failure branch (when `gh workflow run` exits non-zero, check billing API). Not a standalone Step 9H. Park for Step 9G follow-up.

---

## Idea 3: Tenant-Silence Alert via Nightly Step

### Challenge
- Requires Supabase MCP access in headless/nightly context. Prior runs (87-88) confirmed Supabase MCP unavailable in headless sessions.
- PR #575 already proposes this via a frontend admin view + backend endpoint. Adding a nightly SKILL.md step in parallel could conflict with PR #575's implementation approach.
- PR #575 is draft but has 38 tests passing locally. CI is dark due to GH #500 — once that's resolved, the PR can merge. Why add a nightly step when the proper fix is in-flight?
- 3 active Agent OS tenants. Risk of false positives on legitimate quiet periods.

### Defense
- Supabase MCP headless block is a real blocker. The bug-patterns.md entry for run 88 explicitly records this.
- PR #575 conflict: adding a SKILL.md step before PR #575 merges adds redundant monitoring. The right path is to unblock PR #575 by fixing GH #500 (which is the human action), not to shadow it with a nightly step.
- Phase 0 gate concern: PR #575 title includes "Managed Agents Phase 0 prep" — merging it requires review.

### Verdict: WEAKENED → Parking Lot
Blocked by Supabase MCP headless limitation (same mechanism as run 88). PR #575 is the correct implementation path. Park until GH #500 resolved and PR #575 merges.

---

## Synthesis

| Idea | Verdict |
|------|---------|
| Idea 1: Step 9G direct implementation | SURVIVES → WINNER |
| Idea 2: GH spending limit monitor | WEAKENED → parking lot (merge into Step 9G failure branch) |
| Idea 3: Tenant-silence nightly step | WEAKENED → parking lot (wait for PR #575) |
| Idea 4: VOYAGE_API_KEY rotation schedule | Not debated (not top 3 by impact) → parking lot |
| Idea 5: Booking panel first-week audit | Not debated (not top 3) → parking lot |
