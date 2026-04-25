# Debate Log — Run 8 (2026-04-25-pm)

Top 3 ideas ranked by impact: Idea 1 (invariants wire), Idea 2 (JS catch escalation), Idea 3 (widget smoke test).

---

## Idea 1: Wire check_project_invariants.py into Pre-commit Hook

### Challenge Round

**C1: Is the evidence strong enough?**
The script was just added in `037865f` and I only read the first 40 lines. What if the script is incomplete, throws errors on normal commits, or checks invariants that don't match the actual codebase patterns? A buggy pre-commit check blocks ALL commits.

**C2: Is this the highest-leverage thing right now?**
The pre-commit hook already runs 5+ checks. Adding a 6th may suffer from diminishing returns. The implementation lag (5 unimplemented winners) is the larger systemic problem — adding yet another recommendation while the backlog grows is counterproductive.

**C3: What could go wrong?**
If `check_project_invariants.py` has false positives (e.g., catches `tenant_id` in a comment, or in a correctly-named variable in a migration context), developers hit a blocked commit for a non-violation. They'll disable the hook. This is how hooks die.

**C4: Has something similar been tried?**
Run 6 added a migration duplicate-number guard to pre-commit. That was implemented as a WARNING, not a FAIL, precisely because false-positive risk was real. The same caution applies here.

**C5: Is the timing right?**
`037865f` was committed today. The script may not be production-hardened. Recommending it be wired immediately, before it's validated in standalone use, risks noise.

### Defense Round

**D1 (evidence strength):** The script is explicitly described as "safe for CI and for agents" in its docstring. It is stdlib-only with no external dependencies. The invariants it checks (field naming, import patterns) are the exact patterns in CLAUDE.md's Critical Invariants — patterns that have caused 3+ production bugs. The script DESIGN is a match for pre-commit use.

**D2 (leverage):** The implementation lag argument is valid, but wiring a pre-commit check is S-effort (1 bash block added to an existing file). The lag exists because human approval is pending, not because more checks are harmful. This check prevents future bugs regardless of the approval lag.

**D3 (false positives):** Mitigated by: (a) running with explicit exit code check (`if ! python3 scripts/check_project_invariants.py`) which only blocks on script failure or detected violation, (b) the script's stdlib-only design makes crash risk low, (c) if false positives emerge, the fix is in the Python script not the hook. Precedent: `__future__` annotation guard has had zero false positives since wiring.

**D4 (precedent):** Run 6 added migration guard as WARNING because migration numbering is lower-frequency. Invariant violations are higher-frequency (CLAUDE.md says 3+ incidents). A FAIL-mode check is appropriate for a bug class that repeatedly reaches production.

**D5 (timing):** The script was added specifically to be useful to CI and agents NOW — it wasn't marked as a draft or WIP. Wiring it immediately is the intended use.

### Verdict: **SURVIVES**
Evidence triple-backed: (1) script designed for CI use, (2) invariant violations are documented recurring bug class, (3) S-effort with precedent in existing hook. False-positive risk acknowledged but manageable.

---

## Idea 2: JS Silent Catch Guard — Escalation + Moratorium Flag

### Challenge Round

**C1: Is this the highest-leverage thing?**
This is a repeat recommendation from run 3. The system has recommended it twice (runs 3 and 7 parking lot). Each time it doesn't ship. Adding governance overhead (moratorium flag) doesn't fix the implementation — it just adds friction. The real problem is human approval, not lack of recommendation.

**C2: Is the evidence strong enough to recommend a moratorium?**
A moratorium would stop new subconscious recommendations until the catch guard ships. What if there's a higher-priority improvement that emerges next week? Freezing the system on one pending item could cause larger opportunity cost.

**C3: What could go wrong?**
A moratorium flag in governance.json is a recommendation to the human, not a technical enforcement. If the human ignores the moratorium, the system produces no recommendations for runs 9, 10, etc. — dead loops. This pattern could stall improvement velocity entirely.

**C4: Has something similar been tried?**
The `implementation_lag_warning.escalate: true` flag was added in run 7. It produced no implementation. A moratorium flag is the same mechanism with a different name. Escalating escalation has diminishing returns.

**C5: Is this too similar to the current active direction?**
governance.json already has JS Silent Catch as `active_directions` with `pending_approval`. Re-recommending it changes nothing except adding the moratorium concept.

### Defense Round

**D1 (leverage):** The moratorium isn't designed to fix the implementation — it's designed to redirect the subconscious's energy from generating NEW ideas toward surfacing OLD ones. A system that generates 8+ recommendations but implements 2 is net-negative. The moratorium forces recalibration.

**D2 (evidence for moratorium):** 5 unimplemented winners. Oldest pending: Lead Source Analytics from run 2, now 19 days old. JS catch guard: 14 days. The threshold from run 7 ("escalate directly") was hit. Escalation via moratorium is proportionate.

**D3 (moratorium stall risk):** Mitigated by: moratorium config sets `max_pending_approvals: 3` — when pending approvals drop to 3, moratorium lifts automatically. The human can also force-lift via governance.json edit. It's a nudge, not a lock.

**D4 (escalating escalation):** The difference from `escalate: true`: governance.json with `moratorium_active: true` changes the SYNTHESIS phase behavior in future runs — the skill reads governance.json before ideation and would recognize moratorium state. It's a behavior change, not just a flag.

**D5 (active direction):** The moratorium governance itself IS a new recommendation (Idea 5). The JS catch guard angle makes this Idea 2 feel like a vehicle for Idea 5's core value. The ideas should be evaluated separately.

### Verdict: **WEAKENED → Parking Lot**
The JS catch guard re-escalation is correct in spirit but the moratorium mechanism is better captured in Idea 5 (moratorium governance). Idea 2 is redundant: the technical recommendation (Add Check 9 to pre-commit) already exists in the active_directions. The moratorium angle belongs in governance.json update, not in the winning concept.

---

## Idea 3: Smoke-test widget_helpers Split Modules

### Challenge Round

**C1: Is the evidence strong enough?**
The split was done in `6cf4646` (2026-04-18), now 7 days old. Is it actually broken? current-tasks.md says "QA needed" but the app hasn't crashed in production from the split. Maybe the import structure is fine and the risk is overstated.

**C2: Highest leverage?**
current-tasks.md has 25+ QA items. Why is widget_helpers smoke test more important than QA for the compromised API key (day 22), or migration 102 production verification?

**C3: What could go wrong?**
A Python import smoke test that passes doesn't prove production safety. Cross-origin embed behavior (the real risk) requires a browser. A passing smoke test gives false confidence.

**C4: Similar to parking lot items?**
"Widget Hot-Zone Regression Suite" in parking lot covers widget testing with more depth. "Onboarding AI Parser Edge Case Tests" is also a test-writing recommendation. Pattern fatigue: three consecutive test-writing recommendations.

**C5: Implementation vs recommendation?**
The subconscious recommends, doesn't implement. "Write smoke tests" is an implementation action. Recommending it is valid, but the value is lower than recommending a systemic process change.

### Defense Round

**D1 (evidence):** The split is in governance as the ONLY `implemented_unverified` subconscious winner. This is a specific governance commitment to verify. The smoke test is the minimal verification step. Production hasn't crashed doesn't mean it's correct — silent import errors or missing function exports only surface under specific conditions.

**D2 (leverage vs other QA):** The API key is a HUMAN action (Railway rotation), not an agent action. Migration verification requires Supabase MCP. Smoke test is agent-executable. It's the highest-leverage AGENT-ACTIONABLE QA item.

**D3 (false confidence):** Acknowledged. Smoke test is gate 1, not gate 2 (cross-origin browser test). But gate 1 is missing entirely and gate 2 (Widget Hot-Zone Regression Suite) is blocked on Playwright confirmation. Smoke test unblocks gate 2 — it proves the module structure is sound before investing in browser testing.

**D4 (parking lot overlap):** Widget Hot-Zone is Playwright E2E (L-effort). This is Python import smoke (S-effort). Different tools, different verification levels, complementary not duplicate.

**D5 (recommendation vs implementation):** "Write smoke tests for widget_helpers modules" is as atomic and recommendable as any pre-commit hook addition. The implementation is what the human approves and delegates.

### Verdict: **WEAKENED → Parking Lot**
Correct diagnosis: the only `implemented_unverified` governance winner deserves verification. But two objections hold:
1. The QA action is narrower than the systemic improvement — it doesn't prevent future unverified implementations.
2. Idea 1 (invariants wire) is stronger evidence + higher leverage + same S-effort.
Move to parking lot with note: "Promote to run 9 if widget Hot-Zone Regression Suite Playwright path is confirmed."

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| 1: Wire check_project_invariants.py | SURVIVES → **WINNER** | Highest leverage, fresh evidence, S-effort, zero deps |
| 2: JS Silent Catch Escalation | WEAKENED | Core mechanism better as moratorium governance update |
| 3: widget_helpers Smoke Test | WEAKENED → Parking Lot | Correct diagnosis, lower leverage than Idea 1 |
| 4: bug-patterns.md Monthly Split | Not debated (ranked 4th) | Stay in parking lot |
| 5: Moratorium Governance | Not debated (ranked 5th) | Captured in governance.json update this run |
