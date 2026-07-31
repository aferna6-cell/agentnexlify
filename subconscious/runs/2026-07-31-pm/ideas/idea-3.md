# Idea 3: Step 9J — Nightly Autonomy Sweeper Invocation

**Evidence:** Autonomy sweeper (`8e78f5b`, 2026-07-28, PR #608) shipped `scripts/autonomy/sweeper.py` with `find_stranded()` + `sweep()`, plus CLI entrypoint `run_loop.py sweep [--dry-run]`. 251-line test file, 15 tests, 422 total passing. Shipping context: closes GH #605 (crash-stranded runs). Current gap: sweeper is CLI-only. If a Routine fires and the Routine session crashes mid-execution, the run is stranded indefinitely until someone manually runs `run_loop.py sweep`. Run 101 parking lot: "Nightly autonomy sweeper invocation (Step 9I candidate) — structural gap in scripts/autonomy/, sweeper is CLI-only." Run 102 mandate: "check Day 7+ from 2026-07-28 ship date — promote to winner if no automated sweep exists." Today is Day 3 (2026-07-31 − 2026-07-28), below the Day 7+ threshold.

**Action:** Add Step 9J bash block to `.claude/skills/nightly-commit-review/SKILL.md`. Block: run `python3 scripts/autonomy/run_loop.py sweep --dry-run` first; parse output for stranded run count; if N > 0, run `python3 scripts/autonomy/run_loop.py sweep` and log result; if N == 0, log "Step 9J: autonomy sweeper — 0 stranded runs." Idempotent. ~20 bash lines. Uses same REENTERABLE_NODES/NON_REENTERABLE_NODES logic already in `loop_graph.py`.

**Impact:** Auto-recovery of crash-stranded Routine runs without human intervention. Structural resilience for the autonomy pipeline. Expected: ~0-1 stranded runs per week given current Routine cadence; each recovered run prevents a 24h+ stall in the autonomous engineering loop.

**Category:** workflow

**Constraint:** Run 102 mandate says Day 7+ threshold for promotion. Today is Day 3. Proposing early — debate will determine if premature.
