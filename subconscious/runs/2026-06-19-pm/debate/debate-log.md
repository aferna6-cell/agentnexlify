# Debate Log — Run 62 (2026-06-19-pm)

Top 3 ideas by impact: Idea 1 (GH #292/#293 mandate), Idea 2 (GH #308 carry-over),
Idea 3 (GH #263 pending migrations).

---

## Idea 1: Fix GH #292/#293 — Wire chatbot/agent_os into Plan-Name Dicts

### Challenge Round 1: Evidence strength
> GH #292/#293 has been in the parking lot since run 59. Is the evidence different now
> than it was then, or is this just a mandatory pivot from a governance rule?

**Defend:** Three direct grep confirmations this run:
- `sms_rate_limiter.py:10` confirmed old plan names (growth/professional/autopilot/enterprise)
- `api_key_auth.py:29` confirmed old plan names — chatbot/agent_os absent
- `billing_reconciliation.py:33-48` confirmed old plan caps table — no chatbot/agent_os keys
The mandate is governance-binding (same 4-consecutive-run threshold that fired at run 34/35
for GH #181, which correctly pivoted from GH #181 to email_sequences split). New evidence:
billing repriced 3 days ago, meaning every signup since 2026-06-16 is affected. Scope has
grown, not shrunk.

### Challenge Round 2: Is the fix actually 10 min?
> billing_reconciliation has two separate cap tables (_PLAN_AGENT_RUN_CAPS and
> _PLAN_BASELINE_AI_TOKENS). What are the correct values for chatbot and agent_os?
> Without knowing the values, "10 min" is optimistic.

**Defend:** The fix for sms_rate_limiter and api_key_auth is trivially safe — both are
set membership checks where the new plans should get the same unlimited/allowed status
as prior paid plans. billing_reconciliation caps require a product decision on the values:
- chatbot ($19.99/mo) should map to ~growth tier caps
- agent_os ($99.99/mo) should map to ~autopilot-professional tier caps
The implementation sketch should flag the cap values as needing product input and use
safe defaults (growth-tier minimums) if no product guidance is available.
~10 min for sets, +10 min for cap-table values with conservative defaults = ~20 min.
Still lower activation energy than GH #308 (~20 min with regression test requirement).

### Challenge Round 3: Leverage — is this the highest-leverage thing?
> GH #308 is a revenue bug (dunning-lock after card fix). GH #292/#293 affects new
> paid tenants who are already signed up wrong. Both are urgent. Why switch?

**Defend:** Two reasons:
1. Governance mandates the switch. 4 consecutive cycles of GH #308 without implementation
   — the governance system correctly identifies this as an activation-energy problem, not
   an information problem. Pivoting to a lower-energy task is the proven unlock (same
   pattern as runs 48/49/50 on em-dash fix).
2. GH #308 has a complete implementation sketch across 3 winning-concept.md files.
   Any human spending 20 min can implement it from the existing docs. GH #292/#293 needs
   a fresh sketch to document the correct cap values.

**VERDICT: SURVIVES → WINNER**

---

## Idea 2: Fix GH #308 — Webhook Idempotency (4th carry-over)

### Challenge Round 1: Governance compliance
> Recommending GH #308 for the 4th time violates the run 62 mandate. Governance integrity
> requires honoring the mandate — otherwise the mandate mechanism is meaningless.

**Defend:** The mandate is advisory based on activation-energy theory, not a hard block on
the analysis. GH #308 is a revenue bug. GH #292/#293 is a feature-availability bug. Revenue
bug is higher severity.

### Challenge Round 2: Mechanism analysis
> If the mechanism is broken (3 cycles, nightly non-autonomous, human non-implementation),
> recommending again without a mechanism change is definition of insanity. Run 35 applied
> the same pivot from GH #181 — that worked.

**Defend:** No counter. Mechanism is genuinely broken. GH #308 remains critical and the
implementation sketch is complete — it needs human execution, which the mandate
(lower-energy task first) is designed to unlock.

### Challenge Round 3: Outcome
> Should this stay as Bonus A with full implementation sketch?

**Defend:** Yes. Bonus A status preserves visibility, keeps the sketch live, and provides
the action as a "next 20 min" item after the main winner is done.

**VERDICT: WEAKENED → Bonus A (mandate compliance)**

---

## Idea 3: Investigate GH #263 — 24 Pending Migrations

### Challenge Round 1: Actionability
> "Investigate" is not an atomic action. What does a subconscious winner
> look like that is "investigate X"?

**Defend:** Investigation produces a GH issue or an audit doc. But the issue hasn't been
triaged enough to know what fix to recommend. Proposing "fix 24 migrations" without knowing
which ones are safe to apply is a half-migration (Rule 8 violation).

### Challenge Round 2: Competing priority
> Given run 62 mandate fires for GH #292/#293, and Bonus A covers GH #308,
> does #263 need to be the winner? Or is it a future-run candidate?

**Defend:** #263 is CRITICAL but the scope is unclear. It could be schema drift, stale
tracking, or migration conflicts. Wrong to make it the winner without triaging it first.
Better as a parking lot item with a "next run investigate" note.

**VERDICT: WEAKENED → Parking Lot (insufficient triage, future run candidate)**

---

## Synthesis

| Idea | Verdict |
|------|---------|
| Idea 1: GH #292/#293 plan-name dicts | **SURVIVES → WINNER** |
| Idea 2: GH #308 carry-over | WEAKENED → Bonus A |
| Idea 3: GH #263 pending migrations | WEAKENED → Parking Lot |
| Idea 4: PR #333 review | Not debated → Standing operational action |
| Idea 5: Plan-name guard check 7 | Not debated → Bonus B (AUTONOMOUS-EXECUTABLE after Idea 1) |
