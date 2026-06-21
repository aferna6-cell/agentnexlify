# Debate Log — 2026-06-21 (Run 65)

Top 3 by impact: Idea 1 (GH #308), Idea 2 (GH #292/#293), Idea 3 (KB stale fix).

---

## Idea 1: Fix GH #308 — Webhook Idempotency Early-Write

### Round 1

**Challenge:** This has been recommended 7 consecutive cycles without implementation. The alternating mandate switched to GH #292/#293 in run 64 — that also wasn't implemented. Is there evidence that switching back to GH #308 changes anything? The mechanism seems stuck regardless of which bug is the "winner."

**Defend:** The mandate system exists precisely to maintain pressure on both bugs without letting either drop off the radar. Run 64 winning-concept.md §RUN 65 MANDATE is unambiguous: "if GH #292/#293 still unimplemented → switch winner back to GH #308." Governance consistency is the only reliable signal in a system where human scheduling is the bottleneck. Additionally, GH #308 is objectively higher severity: a permanent revenue leak (payment events silently dropped) vs. a wrong-limit bug (GH #292/#293). Both matter, but #308 is a data-loss class bug.

### Round 2

**Challenge:** The fix is ~10 lines and has been documented since run 59. If it hasn't been implemented in 7 cycles, the blocker isn't information clarity. Is there a structural reason it keeps getting skipped — risk aversion on Stripe code, wrong assignee, competing priorities?

**Defend:** The nightly review correctly declines to auto-implement because it "touches Stripe payment handling" — this is non-autonomous by design, not by failure. The blocker is human scheduling of a MEDIUM-risk task, not ambiguity. The mandate keeps it visible. The fix sketch is complete: add `delete_key()` to `idempotency.py`, call in `stripe_webhooks.py` exception handler before re-raising. Regression test spec is written. Nothing new to document.

### Round 3

**Challenge:** GH #292/#293 affects every new paid signup right now (active product breakage). GH #308 affects a narrow path (handler failure during Stripe retry). Which has higher active customer impact today?

**Defend:** GH #308 is higher severity class: permanent data loss vs. wrong rate limit. A tenant who fixes their credit card and stays dunning-locked has zero recourse from their end — they paid, the payment registered, but the webhook event was dropped. GH #292/#293 is annoying (wrong SMS limits) but fixable with a support ticket. GH #308 silently corrupts the billing recovery flow. Mandate compliance + severity class both point to #308 as winner.

**Verdict: SURVIVES → WINNER**

Rationale: Mandate compliance (run 64 governance), higher severity class (data-loss vs. wrong-limit), complete implementation sketch, nightly review correctly declines auto-fix (by design). 7th consecutive recommendation — human scheduling is the confirmed bottleneck, not information.

---

## Idea 2: Fix GH #292/#293 — Wire chatbot/agent_os into Plan-Name Dicts

### Round 1

**Challenge:** Idea 1 won on mandate and severity. Idea 2 is Bonus A per mandate hierarchy. Is there any argument that Idea 2 should displace Idea 1?

**Defend:** No — mandate hierarchy is clear. Idea 2 is correctly positioned as Bonus A. The mandate alternation exists because neither bug has been fixed; the system switches between them to maintain pressure on both. This run, GH #308 is winner. GH #292/#293 is the highest-priority bonus action.

### Round 2

**Challenge:** The "product decision" blocker (what SMS limit for chatbot plan?) has been cited in prior runs. Is this genuine ambiguity or a scheduling excuse?

**Defend:** The implementation sketch in `subconscious/runs/2026-06-19-pm/winning-concept.md` proposes parity-tier defaults (chatbot = growth-level SMS cap, agent_os = unlimited). The product decision is a 5-minute confirmation, not a blocker. The sketch is complete enough to merge with a PR comment asking for confirmation. This is not genuine ambiguity.

### Round 3

**Challenge:** 3 cycles as winner/Bonus A without implementation. Is there any new evidence that changes implementation probability?

**Defend:** No new evidence. Implementation probability unchanged from prior runs. However, Idea 2 as Bonus A is the correct framing for runs where GH #308 is the mandate winner. If GH #308 gets fixed in the same session, Idea 2 should be the immediate next action.

**Verdict: WEAKENED → Bonus A**

Rationale: Mandate hierarchy places this as Bonus A. Survives debate on merit — active product breakage, complete sketch, parity defaults reduce the "product decision" activation energy. Implementation probability unchanged.

---

## Idea 3: Fix kb-autopopulate.sh — KB 46 Days Stale

### Round 1

**Challenge:** Revenue bugs (Idea 1 + 2) take priority by mission brief ordering. KB staleness is operational, not customer-facing in the same immediate way. Can this compete with two confirmed production bugs?

**Defend:** KB staleness has a direct customer-facing impact: AI widget responses cite retired plan names (autopilot, professional, $150/$250) instead of current 2-plan model (chatbot $19.99, agent_os $99.99). Customers in the widget may be confused about pricing. The root cause (agent-browser CLI not installed) is solvable by patching the script to use WebFetch MCP.

### Round 2

**Challenge:** If the fix required installing agent-browser CLI (which was the root cause per run 53), can this actually be fixed in a scheduled run? Does WebFetch MCP work in the nightly review context?

**Defend:** This is a genuine uncertainty. The nightly review has WebFetch as a tool, but kb-autopopulate.sh calls the agent-browser CLI binary. Patching the script is feasible but would need testing. The autonomous path is uncertain — this likely needs a human to fix the root cause first.

### Round 3

**Challenge:** 46 days stale but no customer complaints logged in nightly reviews about incorrect plan citations in widget. Is the impact confirmed or theoretical?

**Defend:** No direct evidence of customer complaints — impact is inferred. Widget prompts may include plan names from the tenant's config (not KB), so KB staleness may matter less for pricing than for product feature descriptions. Impact is real but uncertain in magnitude.

**Verdict: WEAKENED → Parking Lot**

Rationale: Uncertain autonomous path (agent-browser CLI dependency), no confirmed customer impact from staleness, revenue bugs outrank operational health this cycle. Promote for evaluation in next cycle where mandate bugs are resolved.

---

## Synthesis

- Idea 1 (GH #308): SURVIVES → **WINNER** (mandate + severity)
- Idea 2 (GH #292/#293): WEAKENED → **Bonus A** (mandate hierarchy, active breakage)
- Idea 3 (KB stale): WEAKENED → **Parking Lot** (uncertain path, outranked)
- Idea 4 (AI-to-Human Handoff): Not debated → **Parking Lot** (M-effort, moratorium active, no new evidence since run 38)
- Idea 5 (Tenant checklist): Not debated → **Parking Lot** (valid, lower urgency vs. active revenue bugs)

### RUN 66 MANDATE

If GH #308 still unimplemented: switch winner to GH #292/#293 (alternating mandate continues). Implementation sketch: `subconscious/runs/2026-06-19-pm/winning-concept.md`.
