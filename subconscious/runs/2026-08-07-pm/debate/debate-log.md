# Debate Log — Run 103 (2026-08-07-pm)

## Top 3 Candidates

Ranked by initial confidence: **B > C > A**

B: Appointment Brief AI Usage Guard (confirmed LLM gap in new service)
C: Grandfathered Plan Gate Audit (mandate item, speculative until grep)
A: feature-docs-trio Skill (mandate item, workflow quality)

D (Step 9H) pre-killed — alerting about alerting, human attention problem, no production risk.
E (Nightly scanner) survives weakened — powerful meta-prevention but more complex than one targeted fix.

**Clarification (post-read of response_score.py):** Initial grep on `response_score.py` suggested LLM calls missing a guard, but re-read of the service confirmed "no LLM, no new tables" in the docstring — it's deterministic. The confirmed LLM-calling gap is in `appointment_brief.py` (two `call_claude_messages` calls, BRIEF_MODEL = "claude-sonnet-5"), which has zero plan gating in service or router.

---

## Debate Round 1: Idea B vs. Idea C

### FOR B (appointment_brief.py ai_usage_guard)
1. **Confirmed production gap.** `appointment_brief.py` imports and calls `call_claude_messages` twice (lines 119, 150) with `BRIEF_MODEL = "claude-sonnet-5"`. Grep for ai_usage_guard/check_usage/plan_check/block_demo in service and router returns zero results.
2. **All three guards missing.** Not just plan gating — `block_demo_role` and `ai_usage_guard` are both absent. The router only has `_get_current_tenant` (auth). This is worse than the buy-usage issue (which had only block_demo_role missing).
3. **Shipped 24h ago.** e0e9be6 landed 2026-08-06. Gap is new and active.
4. **Cost exposure is real.** Two Claude Sonnet 5 calls per appointment brief. Any tenant on chatbot plan ($19.99/mo — "widget/chat only"), free/lapsed, or demo role can trigger these. At $3/M input tokens, high-frequency call sites with 0 gate.
5. **Exact fix pattern exists.** `billing_usage.py` fix (nightly-2026-08-07): `dependencies=[Depends(block_demo_role)]` + `ai_usage_guard` usage. Mirror this to `appointment_briefs.py` router + add plan feature check for `appointment_briefs` as agent_os feature.

### AGAINST B
1. **Not explicitly in mandate.** run_103_mandate names feature-docs-trio and grandfathered audit as candidates.
2. **Code change requires human.** Subconscious recommends; issue-to-pr-loop implements.
3. **S effort.** Two files (service + router), one import, two dependency injections, one test.

### VERDICT ON AGAINST-B
- Point 1: Mandate specifies candidates, not lock. Run 103 mandate overrides run 102 choice. This overrides mandate when production gap confirmed.
- Point 2: All winners are recommendations. Objection applies equally to all.
- Point 3: S effort is within range for confirmed production risk.

**B SURVIVES.**

---

## Debate Round 2: Idea C vs. Idea B

### FOR C (Grandfathered Plan Gate Audit)
1. **Mandate-directed.** run_103_mandate item #6 explicitly calls this a run 103 candidate.
2. **Paying grandfathered tenants could be wrongly blocked.** New feature gate checking `plan == "agent_os"` without `growth/autopilot/professional/enterprise` silently 403s legacy contracts.
3. **Grep-only.** Audit produces the finding; human fixes.

### AGAINST C
1. **Speculative.** We don't know if actual gaps exist without running the audit. B is confirmed.
2. **Low urgency if clean.** If all plan gates are correct, C is noise.
3. **B affects ALL tenants, C affects only grandfathered subset.** Per governance, 2-3 agent_os tenants currently — small grandfathered pool.

**B WINS over C.** C → backlog for run 104.

---

## Debate Round 3: Idea A vs. Idea B

### FOR A (feature-docs-trio Skill)
1. **Mandate-directed.** run_103_mandate item #5.
2. **Systematic prevention.** SKILL.md channel — proven for Steps 9A-9G.
3. **3 occurrences in 7-day window.**

### AGAINST A
1. **Docs are retroactively fixable; unguarded LLM calls leak money immediately.**
2. **Trigger definition is hard.** "feature shipped = doc needed" requires judgment; false positives on refactor commits.
3. **Soft discipline gap vs. hard cost exposure.** B wins on urgency.

**B WINS over A.** A → parking lot for run 104.

---

## Idea D (Step 9H) Re-examination

**Kill test:** "What if we never add Step 9H?" → PRs continue to pile up. 7 open now. Pattern has persisted 35+ cycles.

**Counter-kill:** Step 9H alerts have been proposed 3 times (runs 100, 101, 102). Human hasn't merged any of the 6 subconscious PRs. A 4th alert on the same channel doesn't change the constraint. The constraint is human review time, not alert visibility.

**D KILLED.** Human attention problem, not an information problem.

---

## Final Verdict

| Idea | Outcome | Reason |
|------|---------|--------|
| A — feature-docs-trio | Parking lot | Valuable but lower urgency than confirmed production gap |
| B — response_score.py ai_usage_guard | **WINNER** | Confirmed production cost exposure, 24h post-ship, clear fix |
| C — grandfathered plan gate audit | Backlog (run 104) | Valid mandate item, speculative, low urgency |
| D — Step 9H PR alerter | Killed | Human attention problem; 3rd-proposal, no new mechanism |
| E — Nightly ai_usage_guard scanner | Promoted to parking lot | Strong meta-prevention; better after B is fixed first |

**Winner: Idea B — Nexlify Score AI Usage Guard**
