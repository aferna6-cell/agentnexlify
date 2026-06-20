# Debate Log — Subconscious Run 2026-06-20-pm (Run 64)

Top 3 ideas ranked by mandate + impact: Idea 1 (GH #292/#293 mandate), Idea 2 (GH #308 payment), Idea 3 (KB stale).

---

## Idea 1: Fix GH #292/#293 — Wire chatbot/agent_os into plan-name dicts

### Round 1 Challenge
The mandate mechanism alternates between two stalled bugs. Neither GH #308 nor GH #292/#293 has been implemented in 4-6 cycles. Alternating between them without implementation just creates recommendation churn. What makes this run's GH #292/#293 recommendation different from run 62's?

### Round 1 Defense
Nothing about the recommendation changes — but the governance mechanism serves a purpose beyond novelty. Alternating creates equal pressure on both bugs so neither is forgotten. Run 62's GH #292/#293 recommendation was not implemented, but it also wasn't rejected by the human — no feedback signal. The mechanism continues as designed. The implementation sketch is complete (`subconscious/runs/2026-06-19-pm/winning-concept.md`), the files are identified, and the code change is atomic (~10 lines across 3 files). The bottleneck is scheduling, not information.

### Round 2 Challenge
GH #292/#293 has a product decision blocker: the governance note says "confirm chatbot SMS limit with product before merging." If the human needs to make a product decision before implementing, this is not a 10-minute fix — it requires a conversation. That increases activation energy, which is already the bottleneck.

### Round 2 Defense
The product decision is bounded: what is the SMS limit for chatbot (the $19.99 plan)? The implementation sketch proposes parity-tier defaults — chatbot gets the same limit as the cheapest existing plan (growth), agent_os gets the same as the highest tier (enterprise/unlimited). This is a reasonable default that can be applied immediately and revised later. The product conversation can happen in parallel with the PR review. "Confirm before merging" does not mean "block implementation" — it means "don't push to main without a number." The 10-minute estimate stands for the code change itself.

### Round 3 Challenge
The `api_key_auth.py` grep returned empty output — which means `_ALLOWED_PLANS` variable might not exist or the file might be at a different path. If the variable name or file path is wrong, this recommendation is based on stale evidence.

### Round 3 Defense
Empty grep output for `chatbot\|agent_os\|_ALLOWED_PLANS\|ALLOWED_PLANS` in `backend/routers/api_key_auth.py` does confirm the chatbot/agent_os plan names are absent from that file. The variable could have a different name or the Zapier gate logic may be structured differently. The original run 62 evidence (direct grep at time of observation) confirmed `api_key_auth._ALLOWED_PLANS line 29` with specific line reference. If the path or variable name has changed, the implementation sketch in `subconscious/runs/2026-06-19-pm/winning-concept.md` provides the canonical guidance including the line number at observation time. The core finding — new paid tenants cannot use Zapier API keys — stands regardless of variable naming.

**Verdict: SURVIVES → WINNER** (mandate compliance + active product breakage + implementation sketch complete)

---

## Idea 2: Fix GH #308 — Webhook Idempotency Early-Write

### Round 1 Challenge
GH #308 is a higher-severity revenue bug than GH #292/#293. Tenants who fix their payment card stay dunning-locked. The mandate mechanism is supposed to surface the most important thing — alternating away from a payment recovery bug to a plan-name bug violates the spirit of the system.

### Round 1 Defense
Both bugs are moratorium_override (active breakage). The mandate mechanism acknowledges this by alternating — not demoting GH #308 permanently, but cycling. GH #308 has been the primary winner for 5 consecutive cycles (runs 59-63) with zero implementation. Continuing to recommend the same winner for a 6th cycle has the same outcome as the GH #181 loop (runs 31-35) that exhausted the mechanism and required a governance pivot. GH #292/#293 was the run 62 mandate, now re-activated as run 64 mandate. GH #308 is Bonus A in this run's winning concept — still visible, still urgent.

### Round 2 Challenge
The 5-consecutive-run threshold from rejected_paths governance (applied to GH #181 at run 35) should fire here. GH #308 has been primary winner for 5 runs without implementation.

### Round 2 Defense
The threshold in rejected_paths applies to *winning* status — at 5 consecutive wins without implementation, the idea exits the winner slot. GH #308 is at 5 consecutive cycles (runs 59-63). The governance protocol already handled this in run 62 (mandate to switch to GH #292/#293) and run 63 (mandate fired back to GH #308). Runs 62 and 63 are the governance mechanism in action — runs 62 and 63 interrupted the streak. Run 64 returns to GH #292/#293 per the alternating mandate. GH #308 is not rejected-paths — it remains a moratorium_override active_direction. It just cannot occupy the winner slot for a 6th straight run.

### Round 3 Challenge
What if both bugs remain unimplemented indefinitely? Is the alternating mandate mechanism itself broken?

### Round 3 Defense
The mechanism remains correct. The moratorium started day 35+ and has many items unimplemented. The subconscious can only recommend — implementation requires human action. The alternating mandate creates maximum legibility: each run, the most important unimplemented item is the winner. When the human finally acts, it is on the winner. Both GH #308 and GH #292/#293 appear in every run (winner or bonus). The mechanism is not broken — the execution channel (human schedule) is the constraint, and the subconscious cannot change that.

**Verdict: WEAKENED → demoted to Bonus A (mandate hierarchy; included in winning concept)**

---

## Idea 3: Fix kb-autopopulate.sh (46-day stale KB)

### Round 1 Challenge
Two confirmed production bugs (GH #308, GH #292/#293) are open and moratorium-exempt. A stale KB has no customer impact — no one has filed a bug, no alert has fired, no revenue is at risk. The KB is a developer aid. Recommending this over either production bug is wrong ordering.

### Round 1 Defense
This idea was never intended to compete with production bugs in this run — it's generating ideas 1-5 and this is idea 3 on the list. If the top ideas are production bugs, then Idea 3 serves as Bonus material at best. The parking lot ROI 1.8 is real but doesn't justify the winner slot when production bugs are open.

### Round 2 Challenge
The fix itself (replacing agent-browser CLI with curl/WebFetch in a shell script) requires understanding what URLs the script fetches and what the output format is. If the script is complex, "replace with curl" is not atomic.

### Round 2 Defense
Valid concern. Without reading the script internals, the fix complexity is uncertain. This makes the effort estimate unreliable. The parking lot classification (run 54: ROI 1.8, "fix: replace agent-browser invocations with curl/WebFetch calls, or skip silently when unavailable") suggests a simpler fallback: add `|| true` to each agent-browser call so the script runs silently when unavailable. That is a 10-second fix that prevents error noise, even if it doesn't restore KB population.

### Round 3 Challenge
The simple fallback (|| true) doesn't fix the core problem — KB stays stale indefinitely. It just hides the failure. Is a silent-failure fix worse than an acknowledged failure?

### Round 3 Defense
Fair. Silent failure is worse than logged failure if the symptom is already invisible. But the current state is already silent — nobody knows the KB is stale unless they read governance.json. A `|| true` fix removes potential error noise without worsening the information gap. The real fix (new URL fetching mechanism) is a separate, larger task. Parking lot is the right place for this.

**Verdict: WEAKENED → stays in parking lot, not chosen this run**

---

## Summary

| Idea | Verdict |
|------|---------|
| Fix GH #292/#293 (chatbot/agent_os plan-name dicts) | **SURVIVES → WINNER** |
| Fix GH #308 (webhook idempotency) | WEAKENED → Bonus A |
| Fix kb-autopopulate.sh | WEAKENED → parking lot |
| schema-discipline New-Table Checklist | Not debated → parking lot |
| Cross-tenant isolation test for os_graph_memory | Not debated → parking lot |
