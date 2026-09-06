# Debate Log — Run 116 (2026-09-06)

Top 3 ideas debated: Idea 1 (Step 9L carry-forward), Idea 2 (os_tool_executions split), Idea 3 (Step 9J token budget fix).

---

## Idea 1: Step 9L — AI Metering Coverage Nightly Check

### Challenge Round 1: Is the evidence strong enough?

**Attack:** Step 9L was already the winner in run 115. Run 116 is just a mechanical carry-forward. Is new evidence truly present, or is this a repeat of the same stale data?

**Defend:** Evidence is materially stronger than run 115: (1) `grep -c 'Step 9L'` → 0 confirms absence in SKILL.md today, not inferred. (2) Nightly-2026-09-06 ran this morning and did NOT fire Step 9L — absence is operationally confirmed, not theoretical. (3) The 7 emergency retrofit PRs (#792–#799) landed in the evidence window (last 7 days). (4) The 13 unguarded routers confirmed by run 115-pm direct grep are still unguarded (no metering PRs since #799, confirmed by nightly-2026-09-06 showing no AI metering commits). Evidence is current and direct.

### Challenge Round 2: Is this the highest-leverage thing right now?

**Attack:** The os_tool_executions split is also Rule 9-critical (1194L combined). God classes accumulate bugs faster. Maybe structural debt is higher priority than billing visibility?

**Defend:** Billing vulnerabilities have active cost consequence every time a new AI route is added without a guard. The 7-PR emergency sprint (#792–#799) cost an estimated 6,000+ lines of test code in 3 days. God class debt accumulates passively — os_tool_executions.py hasn't had a bug in 7 days, hasn't grown in 7 days. The billing gap has active velocity: new AI routes land every release cycle. Step 9L stops active hemorrhage; os_tool_executions split is preventive maintenance. Billing wins.

### Challenge Round 3: What could go wrong?

**Attack:** The AST-based detector could have false positives. Filing GH issues for exempt functions (test helpers, scaffolding) would create noise and erode trust in the nightly sweep. Same problem that made Step 9I's first week rough.

**Defend:** The implementation sketch from run 115 includes three layers of false-positive prevention: (1) `EXCLUDE_DIRS` for test/, docs/, scripts/offline/, knowledge-base/, _archive/; (2) `METERED_WRAPPERS` set for recognized canonical wrappers; (3) per-function `# ai-metering-exempt: <owner>: <reason>` marker. The detector operates at enclosing-function granularity (not file level), resolves aliases, and requires FULL lifecycle (reserve + record + release) — partial guards are correctly flagged. The dedup guard (search_issues before filing) prevents duplicate issues. Regression fixtures in the implementation sketch prove 11 cases including the tricky ones (partial lifecycle, alias, bare exempt). This is a more sophisticated detector than Step 9I (grep-based) — false positive risk is lower, not higher.

### Challenge Round 4: Has something similar been tried and rejected?

**Attack:** Has the "nightly guard sweep" pattern ever failed or been deemed too noisy?

**Defend:** Step 9I (block_demo_role sweep, same mechanism, same pattern) has been in production since run 107 (2026-08-19). Zero false-positive issues filed in 2+ weeks per mandate checks through run 115. Zero governance entries about Step 9I noise. The pattern is proven. Step 9L is the second instantiation, not the first experiment.

### Verdict: **SURVIVES** — dominant winner. Governance mandate fires (`autonomous_executable_run: 116`). No credible attack stands.

---

## Idea 2: os_tool_executions.py God Class Split

### Challenge Round 1: Is the evidence strong enough?

**Attack:** 783L + 411L is large, but does size alone justify a split? The file hasn't had a bug in 7 days. Doesn't "stable" mean "don't touch it"?

**Defend:** CLAUDE.md Rule 9 is clear: >600L + new responsibility = split first. The service is 783L, over threshold. The question isn't "is it broken?" but "when we next need to add to it, will the 783L blast radius make that safe?" The answer is no. The file is stable NOW because nobody has touched it. That stability ends the moment a new OS tool type is needed.

### Challenge Round 2: Is this the right time?

**Attack:** Backend team is active — PRs #792–#799 all landed this week. Splitting a 783L file while an active sprint is happening risks merge conflicts and introduces risk.

**Defend:** Nightly-2026-09-06 confirms 0 commits touching os_tool_executions.py in the last 7 days. The sprint was focused on billing metering (routers/services unrelated to os_tool_executions). The split window is NOW, during calm. Waiting until the next sprint starts makes conflicts worse, not better.

### Challenge Round 3: Step priority vs. Step 9L?

**Attack:** Given Step 9L has governance mandate and active billing exposure, and given the split is a run 117 candidate by explicit HOLD in ideas.md — should this be chosen over Step 9L?

**Defend:** No. The HOLD in ideas.md is correct. Step 9L prevents active cost accumulation. os_tool_executions split is important but not urgent. It belongs in run 117.

### Verdict: **WEAKENED** — valid improvement, wrong priority order. Parking lot for run 117.

---

## Idea 3: Step 9J Token Budget Fix

### Challenge Round 1: Is this solvable at the SKILL.md level?

**Attack:** The token budget problem in Step 9J may be session-level (the nightly session runs out of context/tokens before processing all 19 Dependabot PRs). If so, increasing the per-run cap in the SKILL.md text does nothing — the session just hits the limit sooner.

**Defend:** Partial defense: even if session-level, a cap increase from 5 → 10 would allow more PRs to be processed before the limit is hit. But the attack is partly valid — if the session token budget is the binding constraint (not the coded cap), then the fix requires understanding what's being consumed in the session before Step 9J fires. That investigation requires a nightly log analysis this run doesn't have access to.

### Challenge Round 2: Evidence strength?

**Attack:** "17/19 skipped" could mean the cap (5/run) worked as designed — 2 were processed (rebases triggered), 17 were beyond the session capacity at that point. The cap isn't necessarily the problem; the session budget distribution across all 9 steps might be.

**Defend:** Can't confirm without reading the nightly session transcript. The nightly log only says "17 skipped due to token budget" — it doesn't say which step's budget was exhausted or whether it was the explicit cap or the session limit. The fix requires more diagnostic information than is available this run.

### Challenge Round 3: Is this higher leverage than Step 9L?

**Attack:** Even if Step 9J were fully fixed, the benefit is faster Dependabot PR merges (security patches). Step 9L prevents unbilled AI calls. Billing exposure is revenue-critical; security patches from Dependabot are important but not revenue-blocking.

**Defend:** Not a valid comparison — both matter. But given Step 9L is a governance mandate and this is a speculative fix without diagnostic data, Step 9J fix loses in priority ordering.

### Verdict: **KILLED** — insufficient diagnostic data to propose a solution. Needs nightly log transcript analysis first. Parking lot until a nightly log shows the specific step+token where budget is hit.

---

## Final Rankings

1. **Idea 1 — Step 9L**: SURVIVES → WINNER (governance mandate, proven mechanism, active billing exposure)
2. **Idea 2 — os_tool_executions split**: WEAKENED → parking lot (run 117 candidate, HOLD confirmed)
3. **Idea 3 — Step 9J fix**: KILLED (insufficient diagnostic data, speculative solution)
4. **Idea 4 — CLAUDE.md exemption marker docs**: KILLED (subordinate to Idea 1, premature)
5. **Idea 5 — tenant_api_keys client_id sweep**: WEAKENED → parking lot (Step 9M, low ROI relative to Step 9L; revisit after Step 9L proven)
