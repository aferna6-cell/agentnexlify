# Debate Log — Run 55 (2026-06-11)

Top 3 ideas ranked by impact: Idea 1 (Instagram `from __future__`), Idea 2 (Check 10 WARNING mode), Idea 3 (10 em-dash violations).

---

## Idea 1: Fix `channels_instagram.py` `from __future__ import annotations`

### Challenge Round 1
**Objection:** The pre-commit Check 2 already scans staged router files for `from __future__ import annotations`. If this violation slipped through, it means hooks weren't installed in the commit environment. Fixing the file doesn't fix the systemic gap. We'd be treating the symptom.

**Defense:** The systemic gap (hooks not installed in the commit environment) is real and separate. But CLAUDE.md Critical Invariant #5 is explicit: this annotation causes every Pydantic model request in the router to return 422. The Instagram connector is a brand-new 444L router with full Pydantic request/response models — zero tenants have used it yet, so this production bug hasn't caused visible customer impact YET. Fixing it now, before any tenant tries it, is the right call. 1-line delete, bounded, autonomous.

### Challenge Round 2
**Objection:** Has anyone verified this actually breaks? Maybe Pydantic handles deferred annotations gracefully in newer versions. The 172 tests in test_channels_instagram.py might be passing.

**Defense:** CLAUDE.md Invariant #5 was written from a production incident. `from __future__ import annotations` (PEP 563) defers ALL annotations to strings at module load time — Pydantic cannot resolve them for validation. This is not version-dependent; it's a language semantics issue that has burned the project 3+ times. The tests in test_channels_instagram.py use mocking and may not exercise live Pydantic validation. The check_project_invariants script specifically tests for this pattern. Trust the invariant.

### Challenge Round 3
**Objection:** Is this the highest-leverage thing to do right now? The Instagram connector is 1 day old and zero tenants are using it. The moratorium sprint items (Item A/B) have been pending 50+ days. Shouldn't we unblock those instead?

**Defense:** Item A is blocked by check_project_invariants exits 1. This violation is 50% of why it exits 1. Fixing channels_instagram.py + em-dashes (Idea 3 as Bonus A) together restore exit 0 → Item A auto-wires tonight. So Idea 1 IS the fastest path to Item A. Plus it fixes a real bug proactively.

**Verdict: SURVIVES.** Production bug, 1-line change, highest leverage as a combined package with Idea 3.

---

## Idea 2: Wire Check 10 in WARNING Mode

### Challenge Round 1
**Objection:** The nightly SKILL.md explicitly says "Blocked: script fails on em-dash violations. Execute when script passes clean." The Item A governance entry has `autonomous_executable: true` with a pre-condition. Changing to WARNING mode is a scope change that contradicts the governance entry — it requires updating both SKILL.md and governance.json, and potentially re-litigates the decision to make Check 10 a hard gate.

**Defense:** Check 11 and Check 12 were both wired as WARNING mode, not FAIL. The project's pattern is: start new checks as WARNING, upgrade to FAIL after the codebase adapts. Check 10 being intended as FAIL is aspirational, not binding. WARNING mode today is better than FAIL mode in 2 months.

### Challenge Round 2
**Objection:** The real problem is that hooks don't run in the commit environment used for the last few large PRs (7c8825c, a5c65b5). Adding Check 10 to a pre-commit that doesn't execute is cargo-cult safety theater.

**Defense:** This is the strongest objection. If hooks aren't installed in the PR commit env, WARNING vs FAIL is irrelevant for the commits that matter. The tool doesn't solve the root problem.

### Challenge Round 3
**Objection:** This recommendation creates ambiguity. governance.json has active_directions entry with `"autonomous_executable": true` for Check 10 as a HARD exit. Adding a parallel WARNING-mode version would create two versions of Item A in governance, and the nightly would be confused about which to execute.

**Defense:** (No strong defense — the governance complexity objection is valid. The path for Item A is clear: restore exits 0, then wire as FAIL as designed.)

**Verdict: WEAKENED → Parking Lot.** The core objection holds: if hooks don't run in the commit env, mode doesn't matter. And WARNING contradicts the established Item A design. Better path: Idea 1 + Idea 3 restore exits 0 → Item A wires as FAIL tonight as planned.

---

## Idea 3: Fix 10 Em-Dash Violations Batch

### Challenge Round 1
**Objection:** Runs 49 and 54 both had em-dash fixes as winners. Run 49 was implemented (8db33df). Run 54's 3 violations were cleared as a side effect of a5c65b5. Yet here we are with 10 violations. The system is in a recurrence loop — fixing em-dashes one batch at a time without activating Check 10 is the definition of a Sisyphean task.

**Defense:** Agreed on the loop. But this idea's value is NOT the em-dash fix itself — it's that combined with Idea 1 (the primary winner), it restores exits 0, which is the literal key that unlocks Check 10 auto-wiring tonight. This is the last manual step before the self-healing loop activates. The SKILL.md Item A block already contains the Check 10 inline patch. Once exits 0, it auto-applies. After that, future violations are blocked at commit time and the recurrence loop ends.

### Challenge Round 2
**Objection:** There are now 10 violations across 7 files — more than any prior batch. This implies the rate of introduction is accelerating (large feature PRs). Even if Check 10 wires tonight, the next big PR could introduce more before the developer sees the warning.

**Defense:** That's a hooks-not-installed problem (same as Idea 2 Challenge Round 2). But wiring Check 10 is still the correct fix for developers who DO have hooks installed. The net improvement is non-zero.

### Challenge Round 3
**Objection:** em-dash fixing is the 3rd consecutive run with this idea class (runs 49, 54, now 55). Is there new evidence that makes this iteration different?

**Defense:** Yes: (1) volume is 10 vs 3 vs 5 — escalating signal. (2) This run pairing with Idea 1 creates a combined autonomous package that achieves the Check 10 activation, not just the em-dash cleanup. (3) Run 54 was superseded before nightly could execute it — so the nightly mechanism had no chance to apply the fix.

**Verdict: WEAKENED → Bonus A.** Strong as a co-requirement with Idea 1 but not standalone. Not a primary winner because the em-dash recurrence is structural, not addressable by one-off batch fixes. Value here is entirely derived from unlocking Check 10.

---

## Synthesis

**Winner: Idea 1** — Fix `channels_instagram.py` `from __future__ import annotations`.

**With mandatory Bonus A: Idea 3** — Fix 10 em-dash violations.

**Together:** Idea 1 + Idea 3 → check_project_invariants exits 0 → Item A Check 10 auto-wires tonight → self-healing loop activates.

**Parking Lot:** Idea 2 (WARNING mode — valid but contradicts Item A design), Idea 4 (check-widget-sync.sh — pending_autonomous, good candidate for next interactive session), Idea 5 (Home.jsx split — valid but HUMAN-REQUIRED, deferred).

---

## Governance Correction (applied in Phase 6)

- **Run 54 status: `pending_autonomous → superseded`** — The 3 violations targeted (MemoryPanel.jsx:180, AgentOS.jsx:197/224) were cleared as a side effect of a5c65b5 refactoring AgentOS.jsx. However, a5c65b5 introduced 8 new violations and 7c8825c added 2 more (10 total). Run 54's specific fix was superseded before nightly could execute it.
- **`runs_implemented`**: stays at 16 (run 54 was superseded, not implemented).
