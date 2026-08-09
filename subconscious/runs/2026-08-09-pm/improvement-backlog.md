# Improvement Backlog — 2026-08-09-pm (Run 102)

## Active
- **Step 9H: Idempotent PR Pile Alerter** — Add Step 9H bash block to nightly SKILL.md: query open subconscious PRs, idempotency-check last 7 logs, post once-weekly comment on oldest PR if pile is stale. Implement via proven SKILL.md channel.

## Parking Lot (survived debate but not chosen)

- **Extend client_id sentinel to tenant_api_keys** (code_health) — Add `.eq("tenant_id".*client_id` grep to Step 3 for tenant_api_keys + connector_registry. Catches 5th occurrence of most-frequent bug class (4 prior hits). Nuance: the correct sentinel checks the VALUE argument (client_id variable), not just the column name. Achievable with precise grep. Carry forward; low effort, compounding value. [Bonus action: include in Step 9H PR if implementer chooses]

- **GH #500 Diagnostic Comment** (operational) — Post comment on GH #500 connecting billing-limit → Step 9G pending → KB 17 days stale. One-shot; causal chain inferred not confirmed. Human may already know the connection. Include as optional human action once Step 9H is merged, not as next run's winner.

- **Step 9I: Next-Nightly KB Completion Verification** (operational) — If previous nightly log shows Step 9G pending, check most-recent kb-autopopulate.yml run conclusion on next nightly. Closes the 30s-check monitoring gap. Useful but lower priority than Step 9H (mandate) and sentinel (prevents recurrence).

- **Grandfathered plan gate audit for e0e9be6** (customer_value/code_health) — Grep 22-file e0e9be6 sprint (appointment briefs, daily focus, Nexlify Score, usage meter) for `agent_os` gates without grandfathered plans. Same pattern that caught AI Workforce gate gap 2026-07-15. File GH issue with exact file:line refs. Worth running; not urgent enough to beat mandate.

## Rejected This Run
- **Nexlify Score token-burn guard** (false premise, invalidated) — response_score.py is FULLY DETERMINISTIC (pure SQL, no LLM calls). The parking lot item from run 101 was based on incorrect assumption. Closing permanently. Not a candidate for future runs unless Nexlify Score adds LLM evaluation path.

## Questions for Next Run
1. Was Step 9H implemented and merged from this run's winning concept? If yes, did the first nightly with Step 9H fire correctly?
2. Did the GH #500 billing limit get resolved? Is KB autopopulate running clean?
3. Has the client_id/tenant_id sentinel been extended to tenant_api_keys (bonus action from this run)?
4. Any new occurrences of the client_id/tenant_id mixup since 2026-08-01? If 5th occurrence hit, escalate sentinel to CRITICAL.
5. Grandfathered plan gate audit for e0e9be6 sprint — still unrun? Consider as run 103 winner if sentinel extension is also done.
