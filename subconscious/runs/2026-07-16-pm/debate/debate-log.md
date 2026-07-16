# Debate Log — Run 96 (2026-07-16-pm)

Top 3 ideas ranked by impact: Idea 1 (appointment_completion), Idea 2 (BotHealthPage), Idea 4 (referral_activation os_opportunities).

---

## Idea 1: Wire appointment_completion.py (Carry-forward)

### Round 1 Challenge
The run 95 winner was autonomous-executable and nightly did NOT implement it — despite the winning-concept.md containing the full implementation sketch. What's different now? If nightly skipped it once, it may skip it again. Is there any reason to believe tomorrow's nightly will behave differently?

### Round 1 Defense
The nightly review on 2026-07-16 focused on identifying the root cause (GH #454 filed, booking URL and status filter fixes landed) — it was a diagnostic run, not an implementation run. The nightly that fires at 2:37 AM UTC after a subconscious run typically acts on the most recent winning-concept.md. The run 95 winning-concept.md was committed in the same nightly cycle as the diagnostic work — the nightly may not have had time to execute. Run 96's winning-concept.md is the primary signal for the next nightly. Autonomous channel has confirmed this pattern: Steps 9B/9C/9D/9E all implemented within 1 cycle of being written as winning concepts.

### Round 2 Challenge
The Agent OS sprint (7 PRs in 3 days) is where all developer energy is going. Is appointment_completion.py actually a priority, or has the product focus shifted? Maybe the booking chain is less urgent now that Agent OS has taken center stage?

### Round 2 Defense
appointment_completion.py is not a competing feature — it's infrastructure. Without it, every appointment sits "confirmed" forever and the post-booking automations (review requests, rebook) produce zero output. The booking URL fix (6cc3419) was urgent enough to be committed on 2026-07-16. The next logical step in the same chain is appointment_completion.py. Agent OS doesn't replace booking automation — it's a parallel product track. Both matter.

### Round 3 Challenge
The implementation sketch uses `trigger_event("appointment_completed", appt["tenant_id"], appt)`. But the appointments table uses `tenant_id`, while the schema-discipline rule says `client_id not tenant_id` for leads+conversations. Is there a schema consistency risk here?

### Round 3 Defense
schema-discipline.md Rule 1 explicitly scopes the `client_id` requirement to `leads + conversations` tables. The appointments table correctly uses `tenant_id` (confirmed by win-concept.md: "Schema notes: ... appointments use tenant_id"). The winning-concept.md also explicitly says "No migration required. completed_at column and completed status already exist in the schema — verify before assuming." The nightly should verify before implementing. This is well within the LOW-risk autonomous execution class.

**Verdict: SURVIVES — becomes Winner**

---

## Idea 2: Build BotHealthPage.jsx frontend for admin_loop_health

### Round 1 Challenge
This is L effort — a full frontend page. CLAUDE.md daily-skills.md rule says "no code before zero ambiguity" — grill-me before any 2+ file task. A subconscious recommendation can't grill-me; that's a human-session task. Should this even be recommended without a spec?

### Round 1 Defense
The subconscious recommends, not implements. This can be recommended as a "file GH issue with spec" action — a human-approved implementation path. The admin_loop_health.py endpoint is already specced by its own code (214 lines, well-documented). The AdminFunnelPage pattern (PR #417) provides the template. A GH issue with ai-ready label + implementation sketch could go directly to the issue-to-pr-loop once GH #399 is unblocked.

### Round 2 Challenge
The loop-health endpoint was just shipped (22710b3). We don't know if it's wired into the admin frontend already. Maybe it's already being consumed somewhere? And with GH #399 blocking the issue-to-pr-loop, a GH issue with ai-ready label won't get picked up anyway.

### Round 2 Defense
Grep shows admin_loop_health.py is in backend/routers/ — no corresponding frontend file in frontend/src/pages/. It's definitely unwired on the frontend. However, the GH #399 block is a real concern: without AUTOPILOT_GH_TOKEN rotation, the issue-to-pr-loop can't execute. Filing the issue now documents intent but won't produce a PR until GH #399 resolves.

### Round 3 Challenge
Given that appointment_completion.py (run 95 winner) is more urgent and directly revenue-impacting, and BotHealthPage is L-effort with a known blocker (GH #399), isn't this a clear case of the parking lot being the right place for this?

### Round 3 Defense
Correct. BotHealthPage.jsx is valid, well-motivated, and timely given the admin_loop_health endpoint landing. But appointment_completion.py is S-effort, autonomous-executable, and directly completes the booking revenue chain. BotHealthPage is the right run 97 candidate after appointment_completion.py is confirmed implemented.

**Verdict: WEAKENED → Parking Lot. File GH issue as Bonus Action in run 96.**

---

## Idea 4: Add os_opportunities referral_activation rule

### Round 1 Challenge
os_opportunities.py is a DB-query-only service — it reads from leads, invoices, appointments via Supabase SQL. It does NOT have access to environment variables. REFERRAL_REWARD_ENABLED lives in the Railway environment, not in the database. How would os_opportunities.py know if the feature flag is off?

### Round 1 Defense
Could check a config table in the database, or check a widget_configs column for feature flag state. Some feature flags are stored in widget_configs. But REFERRAL_REWARD_ENABLED is a Railway env var, not a DB column. That's the mechanism mismatch.

### Round 2 Challenge
The os_opportunities pattern is "two rules, no LLM — deterministic-first." Adding env-var inspection would require `os.environ.get("REFERRAL_REWARD_ENABLED")` inside what is otherwise a pure DB-query function. This violates the service's architectural pattern. And the referral_rewards table rows are owned records — their existence doesn't indicate activation status.

### Round 2 Defense
Could add a widget_configs.referral_reward_enabled column to support this. But that's a schema change — a migration is required. CLAUDE.md Rule: "Schema changes only via numbered migration files." This has now grown from an XS opportunity suggestion to a migration + service change. The leverage is much lower than originally assessed.

### Round 3 Challenge
Four autonomous GH comments on #413. 0 human responses in 25 days. If GH comments don't move the needle, there's no strong reason to believe an Agent OS suggestion card will be different — especially if the human hasn't opened the Agent OS suggestion cards UI (PR #462, just shipped 3 days ago). This is adding complexity to work around a human decision point that the human simply hasn't made yet.

**Verdict: KILLED — mechanism mismatch (env-var in DB-query service) + schema migration required + human decision bottleneck not addressable by more notification channels. Not in rejected_paths yet (first kill at this specific angle). Log reason for next run.**

---

## Synthesis

Idea 1 SURVIVES → **WINNER: appointment_completion.py**
Idea 2 WEAKENED → Parking Lot (BotHealthPage.jsx GH issue as Bonus Action)
Idea 4 KILLED → referral_activation os_opportunities rule (mechanism mismatch, schema change required, human decision bottleneck)
Idea 3 → Bonus Action (GH #399 Day-14 escalation)
Idea 5 → Parking Lot (Step 9F — valid, AUTONOMOUS-EXECUTABLE, propose run 97 if appointment_completion implemented)
