# Debate — Idea 3: Silent-Green Tenant Heartbeat (Step 9H)

## FOR

**Bug-patterns.md explicitly calls for this.** The Keys Koffee incident (5+ weeks undetected widget failure) and the booking CTA plain-text bug (money path rendered wrong without error) both appear in `docs/dev-knowledge/bug-patterns.md` with the prevention pattern: "every automation/tenant integration needs a heartbeat distinguishing 'ran and found nothing' from 'never ran'." The subconscious exists to prevent recurring bugs. This is the clearest case.

**Revenue impact is direct.** Paying tenants ($19.99–$99.99/mo) receiving zero AI value = churn risk before complaint. The Keys Koffee pattern is: widget silently broken → tenant doesn't complain (thinks "AI is just quiet") → realizes problem after 5+ weeks → churns without traceable cause. A heartbeat converts silent churn into actionable alert.

**Pattern precedent.** Step 9F already queries KB metadata (DB query via supabase). Step 9H extends this to conversations table. The schema is documented: `conversations.client_id` (NOT `tenant_id` — critical invariant honored). The bash channel can run Python with supabase client if SUPABASE_URL + SUPABASE_SERVICE_KEY are available in the nightly environment.

**Not duplicating existing monitoring.** No current check verifies per-tenant conversation activity. Loop health scan (`scripts/loop_health_scan.py`) monitors Agent OS metrics, not widget conversation counts.

**Compounds with agent graph runtime.** The `d7259d4` agent graph runtime (autonomous engineering loop, not yet armed) will eventually touch tenant integrations. Having a heartbeat now means the autonomous system's effects on tenants are observable from day one.

## AGAINST

**Challenge 1: SUPABASE_SERVICE_KEY availability in nightly bash environment.** Step 9F checks KB staleness by reading `knowledge-base/log.md` — a file, not a database query. Step 9H requires an actual Supabase connection with a service role key. Is `SUPABASE_SERVICE_KEY` (or equivalent) set in the nightly execution environment? Unknown. If not, Step 9H silently fails — which is itself a silent-green failure.

*Defense:* This is the strongest objection. The nightly SKILL.md runs in a Claude Code cloud Routine environment. The script `scripts/daily/kb-autopopulate.sh` runs Python with supabase client — so the pattern is proven at the script level. But `nightly-commit-review.sh` itself is a bash script that might not have the same env setup. **If SUPABASE credentials aren't available, Step 9H fails at runtime, not at design time.** This is a real implementation risk.

*Mitigation:* Design the step with a guard: if `SUPABASE_URL` not set, log "Step 9H: SUPABASE_URL not set — heartbeat skipped" and exit 0. Partial value: at least the failure is visible.

**Challenge 2: Schema complexity.** The query needs to:
- Filter tenants to paid plans only (chatbot, agent_os, plus legacy grandfathered plans)
- Use `client_id` NOT `tenant_id` on conversations table (critical invariant)
- Exclude tenants that are genuinely new (< 7 days old) from the alert
- Exclude test tenants / internal tenants

Getting any of these wrong produces noise (false alerts on new tenants, false alerts on internal test accounts) or blindness (filtering out real paid tenants). The schema is defined but the query requires careful construction.

*Defense:* The CLAUDE.md and schema-discipline.md rules are explicit about `client_id`. But bash-embedded Python is harder to validate than a proper test suite. The nightly can't run pytest on its own bash blocks.

**Challenge 3: "0 conversations in 7 days" is a weak signal.** A tenant whose widget is embedded but whose business is genuinely slow (e.g., a seasonal contractor, a business on vacation) would trigger false alerts every slow week. The signal is right for broken widgets but noisy for slow businesses.

*Defense:* True. Could filter to "was active in last 30 days but 0 in last 7 days" — distinguishes stale tenants from genuinely new ones and from seasonally slow ones. But this requires a more complex query.

**Challenge 4: Alert fatigue.** If 3 tenants are consistently slow (no conversations week-over-week), the nightly creates 3 GH issues every 7 days. That's 12 issues/month on the same quiet tenants. Worse than silence.

*Defense:* First-alert-only: check if a GH issue with that tenant ID already exists in last 30 days before creating. Or use a single recurring issue rather than one per tenant. Dedup-able, but adds more query complexity.

## Verdict

HIGH customer impact, MEDIUM execution risk. The customer value case is compelling — the Keys Koffee class failure is the kind of thing that loses tenants silently. BUT the implementation has 3 real risks: (1) Supabase credentials may not be available in nightly bash, (2) schema query complexity, (3) alert fatigue without dedup logic.

**Correct as a MEDIUM recommendation** — needs owner approval and a small implementation sprint to get the Supabase credential question answered and the query tested before deploying.

Evidence score: 8/10. Execution risk: 7/10. Customer impact: 9/10. Implementation readiness: 5/10.
