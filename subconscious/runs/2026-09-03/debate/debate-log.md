# Debate Log — Run 115 (2026-09-03)

Top 3 ideas ranked by impact: Idea 3 (Step 9L), Idea 2 (store tests), Idea 1 (dead code).

---

## Idea 3: Step 9L Auto-enrich bug-patterns.md

### Challenge
1. **Evidence strength?** 5 empty entries is observable but the root cause enrichment quality from nightly triage summaries may be generic. "fix(m8): preserve send_email input" doesn't automatically produce a useful root cause note — the nightly would need to read diffs, which increases Step 9A complexity.
2. **Highest leverage?** The nightly already has Steps 9A–9K. Adding 9L for doc enrichment competes with the pattern of Steps 9x being autonomous health checks. 9L is more of a documentation-write operation.
3. **What could go wrong?** Nightly auto-writes a wrong root cause note. bug-patterns.md is read by future subconscious runs as evidence. A corrupt entry misleads future reasoning.
4. **Tried before?** No — first proposal of this class.
5. **Similar to active direction?** No overlapping active direction.

### Defend
- 5 consecutive empty entries spanning 7 days is strong signal that the human never fills these in manually.
- The nightly already narrates each bug commit in Step 9A triage — the root cause note IS derivable from that triage prose.
- A non-destructive "append only if empty" guard prevents corruption.
- bug-patterns.md is the primary learning source. Empty Details = zero learning value.

### Verdict: WEAKENED
The concern about auto-generated root cause quality is valid. Nightly commit messages often don't expose root cause clearly (e.g., "fix(m8): preserve send_email input" could mean many things). The mechanism would need to read diffs to produce useful notes — that's a non-trivial Step 9A expansion. Parking lot candidate for when a cleaner mechanism exists.

---

## Idea 2: Add `test_os_workflows_store.py`

### Challenge
1. **Evidence strong enough?** Confirmed: no `test_os_workflows_store.py` in the commit. But engine tests (461 lines) may use the store internally through integration test patterns.
2. **Highest leverage right now?** M9.2 just shipped yesterday (2026-09-02). The module is brand-new with no production traffic yet. The urgency of test coverage is lower than it would be for a live-traffic module.
3. **What could go wrong?** Writing store tests now when the store API is still unstable wastes effort. M9.2 is under active development — store.py may change before M9.3.
4. **Effort mismatch?** This is an M-effort task (writing 400+ test lines for a new module). Subconscious winners are optimally XS-S effort.
5. **Has engine.py test coverage any store paths?** Likely yes — engine tests typically call through to store operations.

### Defend
- 429-line DB-touching module is exactly where schema bugs hide (client_id vs tenant_id). Even basic CRUD smoke tests matter.
- M9.2 PR added `check_workflow_planner_import_boundary()` to invariants but no coverage gate — evidence the author knew about gaps.
- Low production traffic is the BEST time to add tests (no production behavior to regress).

### Verdict: SURVIVES but with lower priority than Idea 1
The evidence is real, but the M-effort concern is valid. The correct atomic action is: file a GH issue for store tests with ai-ready label (letting the issue-to-PR loop handle it when GH #399 resolves), not implement them directly in this recommendation.

---

## Idea 1: Fix M9.2 dead code in `derive_workflow_status()`

### Challenge
1. **Evidence strong enough?** Nightly-2026-09-03 explicitly called it out. Direct read of lines 105-110 confirms. The nightly labeled it "not a behavioral bug" — meaning no production risk, so is it even worth recommending?
2. **Highest leverage?** Dead code removal is low-leverage compared to test coverage or workflow improvements.
3. **What could go wrong?** Removing the inner guard could theoretically mask a future bug if the outer guard is ever weakened. (Counter: removing redundant dead code never creates bugs — only keeping misleading dead code does.)
4. **Similar to rejected paths?** No rejected path for dead code cleanup.
5. **Autonomous-executable?** Yes — nightly handles LOW-risk bug fixes in existing files.

### Defend
- The nightly explicitly flagged this and requested human awareness — that's a call to action.
- XS effort: 3-line deletion with a clarifying comment explaining WHY. Net negative LOC.
- The inner guard creates a real maintenance trap: a future developer could "helpfully" remove the outer guard while keeping the inner one, believing the inner one provides protection. Dead code that looks like a guard is actively misleading.
- The nightly deferred it as "new major module" — subconscious backing makes it actionable in the next nightly cycle.
- Pattern: XS effort winners with direct nightly evidence (runs 104, 105) are consistently high-confidence and implement in 1 cycle.

### Verdict: SURVIVES → WINNER
Strongest combination of: specific evidence, lowest effort, directly executable via existing nightly channel, zero risk, addresses a clear trap in new production code.

---

## Summary

| Idea | Verdict |
|------|---------|
| Idea 1: Fix M9.2 dead code | SURVIVES → **WINNER** |
| Idea 2: Add test_os_workflows_store.py | SURVIVES → Parking lot (file GH issue for loop) |
| Idea 3: Step 9L bug-patterns enrichment | WEAKENED → Parking lot (needs cleaner diff-read mechanism) |
| Idea 4: os_tool_executions.py split | WEAKENED → Run 116 candidate (stability condition not met) |
| Idea 5: GH #728 escalation comment | Not debated (lower impact) → Bonus action |
