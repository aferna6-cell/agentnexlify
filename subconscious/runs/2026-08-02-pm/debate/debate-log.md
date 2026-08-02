# Subconscious Run 101 — Debate Log
**Date:** 2026-08-02-pm
**Debating:** Ideas 1, 2, 3

---

## IDEA 1: Step 9G — KB Self-Healing Trigger in Nightly SKILL.md

### CHALLENGE
- "The KB being stale 10 days is not a disaster. Step 9F already fires a GH issue. A human can trigger the workflow manually. Why automate further?"
- "Automating `gh workflow run` from inside the nightly routine means a nightly script is reaching into CI/CD on every stale day. What if the workflow is already running? Double-trigger risk."
- "SKILL.md edits are low-risk but this is the THIRD consecutive run recommending the same thing. Maybe there is a structural blocker (permissions, env variable) that makes the trigger not worth doing and the subconscious is just refusing to admit it."
- "Step 9G could produce a noisy stream of auto-triggered workflow runs if KB stays stale for many consecutive days."

### DEFENSE
- Step 9F fires a GH issue, yes — but GH #403 has been open since run 100 with no human action. The KB is now 10 days stale. Step 9F's alert is not being acted on. Self-healing is the correct next step, not louder alerts.
- Double-trigger risk: solved by checking workflow status before triggering. `gh run list --workflow=kb-autopopulate.yml --status=in_progress --limit 1` — if output is non-empty, skip. One-line guard.
- Structural blocker check: `gh workflow run` requires `AUTOPILOT_GH_TOKEN` (GH #399) — if that secret is missing the trigger would fail silently. But the nightly routine already uses `gh` for issue creation (Step 9B/9C) and those work. Same token. No new secret required.
- Noisy stream: trigger fires ONCE when stale detected, then kb-autopopulate.sh runs and resets `last_run` in log.md. Next nightly sees fresh KB, no trigger. Not a loop.
- Three-carry-forward is evidence of HIGH value, not structural impossibility. Run 99 implemented Step 9F (the alert). Step 9G (self-healing) is the natural next step in the same channel. Each step is atomic.

### VERDICT: STRONG. All objections answered. XS effort, zero new infrastructure, closes KB staleness gap that is CURRENTLY active.

---

## IDEA 2: Connector Token Expiry Health Check (Step 9H)

### CHALLENGE
- "We don't know the actual column names in `gmail_integrations`. If the schema doesn't have `last_refreshed`, the nightly check query will fail at runtime."
- "The `connector_registry` has `last_checked` and `status` — but OAuth refresh tokens don't expire on a fixed clock. Gmail refresh tokens expire when: (a) unused 6 months, (b) revoked by user, (c) 50 active tokens per account. A `last_refreshed > 30d` heuristic is too crude."
- "b67710c just landed 13,916 lines. Adding a nightly connector check immediately after the sprint means we're monitoring code that hasn't even been in production for 24 hours. Let it bake before adding health checks."
- "The nightly review already confirmed `connector_registry.py` tests exist (test_connector_registry.py, 623L). The existing tests and status polling probably already handle expiry detection."

### DEFENSE
- Schema uncertainty is a real problem. The column name `last_refreshed` was inferred, not verified. Before implementing, a schema-guardian pass is required.
- The 30-day heuristic is intentionally conservative. Gmail refresh tokens in practice expire after 6 months of disuse. 30 days is a leading indicator of risk, not a guarantee of expiry. But "crude heuristic" is better than "no detection at all."
- The "let it bake" objection is valid for 48-72 hours. But Step 9H is a RECOMMENDATION for approval — the subconscious doesn't implement. By the time a human approves and executes, the sprint will have baked.
- `test_connector_registry.py` tests the connector registry code — it doesn't test that prod tokens are currently fresh. Test coverage ≠ operational monitoring.

### VERDICT: PLAUSIBLE but LOWER PRIORITY. Schema verification step required before implementation. The connector health check is valuable but is not the most atomic win available this run. Idea 1 has no unresolved schema unknowns.

---

## IDEA 3: Inbox Triage AI Cost Guard

### CHALLENGE
- "This is speculative. We don't have evidence of inbox_triage.py actually causing token blow-up in production. The service just launched (b67710c, <24h old). There may be no tenants even using it yet."
- "Reading 455 lines of inbox_triage.py plus ai_usage_guard.py plus sms_agent.py for pattern matching is S effort with a risk of subtle integration bugs. A bad guard that incorrectly blocks triage on valid emails is worse than no guard."
- "The sms_rate_limiter pattern was built for SMS because SMS has hard carrier limits. Email triage has no equivalent hard external limit. The urgency is lower."
- "Token guard PRs touching the core triage loop need compound-engineering + qa-tester pass. This is not an XS atomic recommendation — it will bloat the scope of a single subconscious run."

### DEFENSE
- Speculative risk is still valid for a preemptive guard. The SMS rate limiter was also added before SMS rate limits were hit in production — that's the correct order. Retroactive guards come after incidents.
- The pattern exists in sms_agent.py. Reading both files and integrating is S effort, not M. The subconscious recommends, humans implement — the effort estimate is for the executor, not this run.
- Token cost for inbox triage IS bounded differently than SMS — but the project has `ai_usage_guard.PLAN_BASELINE_TOKENS` specifically for per-plan AI usage budgeting. Inbox triage is a prime consumer to plug in.
- The "too new to guard" argument is the same argument that produced the silent-green Keys Koffee incident (5+ weeks unnoticed). Early guards > retroactive.

### VERDICT: VALID but NOT THIS RUN. The service is hours old, no production data exists to calibrate limits, and the right timing is after the first full production data cycle (next 1-2 weeks). Idea 3 earns a slot in the improvement backlog, not the run 101 winner position.

---

## SYNTHESIS

| Idea | Challenge answered? | Evidence strength | Effort | Urgency |
|------|---------------------|------------------|--------|---------|
| 1 (Step 9G) | YES — all 4 objections resolved | STRONG (kb stale now, mechanism proven) | XS | HIGH |
| 2 (Connector check) | PARTIAL — schema unknown | MODERATE | S | LOW (service hours old) |
| 3 (Inbox cost guard) | PARTIAL — speculative | MODERATE | S | LOW (no production data) |

**Winner: Idea 1 — Step 9G: KB Self-Healing Trigger**

Rationale: Only idea where all objections were fully resolved in the debate. Currently active evidence (KB 10 days stale, GH #403 open with no human action). Zero new infrastructure. Mandated by run_101_mandate. Proven mechanism. XS effort.
