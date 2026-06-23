# Debate Log — 2026-06-23 (Run 65)

## Context

Both alternating-mandate items are resolved as of 2026-06-21/22:
- GH #308 (idempotency early-write): `3a958e5` — delete_key added, exception handler patched
- GH #292/#293 (chatbot/agent_os plan-name dicts): `29ed1d4`, `57f2bb4`, `c461cef`
- plan_catalog.py now provides canonical plan sets; test_plan_catalog_coverage.py asserts all gates

First free-choice run since run 58 (2026-06-16). Runs 59–64 were all mandated alternating pivots on the two revenue bugs.

---

## Idea 1: Plan-name guard Check 7 to check_project_invariants.py

**Evidence:** GH #292/#293 FIXED by `c461cef`. plan_catalog.py created (3d4c7db). Was already in the queue as "Bonus B, AUTONOMOUS-EXECUTABLE" in runs 59-64, gated on GH #292/#293 landing. Gate drift has caused 4 separate incidents (GH #81, #181, #292, #293). plan_catalog.CURRENT_PAID_PLANS = frozenset({"chatbot","agent_os"}) is canonical.

**Action:** Add 10-line python block to check_project_invariants.py: for each plan-gate dict in sms_rate_limiter, api_key_auth, billing_reconciliation, require all CURRENT_PAID_PLANS are present. FAIL on missing.

**Impact:** Prevents the 5th repricing-triggered gate drift incident. Autonomous — nightly can execute tonight.

**Category:** code_health

### Challenge
- Is this redundant with test_plan_catalog_coverage.py? That already asserts CI coverage.
- Does adding another check to check_project_invariants.py create tight coupling between the checker and plan_catalog structure?
- Is a 5-min item really worth the winner slot when 68-day AI-to-Human Handoff sits open?

### Defend
- test_plan_catalog_coverage.py runs at CI (post-push). check_project_invariants runs at PRE-COMMIT (pre-push). Defense-in-depth: two independent layers catch different moments. CI is bypassed when pushing directly; pre-commit is not.
- Coupling risk is minimal: plan_catalog.py is explicitly "single source of truth" per its docstring. check_project_invariants simply imports CURRENT_PAID_PLANS — no implementation details.
- 5 min for a structural guard with AUTONOMOUS-EXECUTABLE precedent is exactly the right scope for a subconscious winner. It competes on certainty of execution, not just merit.
- This was explicitly deferred as "Bonus B" for 6 consecutive runs — it's not a new idea, it's a deferred commitment finally unblocked.

**Verdict: SURVIVES → WINNER**

---

## Idea 2: Review and merge PR #209 (timing-safe token comparison security fix, agent-service auth.ts)

**Evidence:** PR audit (2026-06-22) explicitly flags: "Note: #209 (timing-safe token comparison) may be a real security fix — review before closing." GH #206 documented the timing attack in agent-service/src/auth.ts. Check 12 (run 52 winner) added a pre-commit WARNING guard, not a code fix. PR #209 was auto-generated in the same cycle.

**Action:** Read PR #209 diff. Determine if it patches agent-service/src/auth.ts to use timingSafeEqual instead of `===` on X-Agent-Token. If confirmed fix: merge. If only scaffolding: close.

**Impact:** Closes the live timing-attack window on X-Agent-Token comparison in agent-service.

**Category:** code_health / security

### Challenge
- Check 12 (pre-commit WARNING) was the run 52 winner and was implemented. Doesn't that already mitigate this?
- PR #209 is labeled "subconscious run 52" suggesting it's an auto-generated draft that may be incomplete or superseded.
- The audit says "may be" a real fix — there's no confirmed evidence it actually patches the vulnerable line.
- Evidence is uncertain: recommending based on an "investigate first" premise means this is more of a standing action than a subconscious winner.

### Defend
- Pre-commit WARNING blocks FUTURE regressions; it doesn't fix the existing `===` on X-Agent-Token in the live codebase.
- agent-service handles real tenant authentication; a timing attack vector there is HIGH severity.
- However, the uncertainty ("may be real") means this can't be the winner without investigation. That investigation itself is the action, which is under-specified for a subconscious winner.

**Verdict: WEAKENED → Bonus Action (investigate then merge or close)**

---

## Idea 3: AI-to-Human Handoff v1 (explicit trigger, run 4, 68 days)

**Evidence:** customer-gaps.md: "AI-to-human handoff — Critical for complex queries — Medium effort". All 7 industry simulations impacted. os_outbound_mirror.py (PR #188) with 152 tests provides delivery layer. Run 38 scoped to ~1 day after PR #188. 68 days as oldest pending item.

**Action:** In widget_chat.py: detect explicit trigger phrases ("talk to someone", "speak to a person", "human help"). Write lead.status → "needs_follow_up". Call os_outbound_mirror.send_sms(owner_phone, f"New lead needs you: {name}"). Fallback to email via send_email if no owner_phone.

**Impact:** Converts the #1 cross-industry customer gap. Closes run 4 (68 days). Prevents qualified leads from being lost when AI can't handle complexity.

**Category:** customer_value

### Challenge
- 8+ prior recommendations without implementation. What changed?
- True pending is still ~9. Adding an M-effort item without clear capacity is risky.
- The moratorium bottleneck was GH #292/#293 + #308. Those are fixed, but "freed capacity" hasn't been demonstrated — no implementation commits in 3 days since fixes landed.
- os_outbound_mirror.py reduces scope but trigger detection + routing is still a half-day of new code.

### Defend
- Both mandate items resolved is the new evidence. The moratorium exit path is now clearer.
- customer_value winner is warranted eventually — this is the right item by every metric.
- However, 8 prior misses without new forcing function suggests the bottleneck is human scheduling, not information. A plan_catalog guard clears the queue faster (5 min vs 1 day), which may create the implementation headroom AI-to-Human needs.

**Verdict: WEAKENED → Parking Lot (first priority after quick wins clear)**

---

## Synthesis

| Idea | Verdict | Disposition |
|---|---|---|
| Plan-name guard Check 7 | **SURVIVES → WINNER** | Execute autonomously tonight |
| PR #209 security review | **WEAKENED** | Bonus action — investigate + merge/close |
| AI-to-Human Handoff v1 | **WEAKENED** | Parking lot — highest customer value, wrong activation energy for this cycle |

Winner: **Plan-name guard Check 7 — add to check_project_invariants.py**.
