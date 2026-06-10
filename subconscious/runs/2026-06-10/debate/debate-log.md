# Debate Log — Run 2026-06-10

Top 3 ideas debated: Idea 1 (em-dash fix → Item A), Idea 2 (tenant scope checklist), Idea 4 (cross-tenant isolation test).
Idea 3 weakened early (operational, autonomous path uncertain). Idea 5 trivially correct (governance bookkeeping, applied in Phase 6, not worthy of a debate slot).

---

## Idea 1: Fix 3 JSX em-dash violations (unblocks Item A Check 10)

### Round 1

**Challenge:** This is a repeat recommendation. Run 49 fixed 5 em-dash violations; now we're back with 3 more. The real fix isn't to keep patching UI strings — it's to wire Check 10 so commits are blocked upstream. Recommending another em-dash patch feels like treating symptoms forever.

**Defend:** The em-dash fix IS the prerequisite to wiring Check 10. Once Check 10 is wired, this class of issue stops. Run 49's fix proved the mechanism works: 8db33df fixed 5 violations autonomously, then nightly extended scope, then Item A was cleared. The problem is the same code commit (c8a0460) that ships Agent OS knowledge graph also ships UI copy with em dashes. Fixing these 3 lines (2 min, autonomous) → exits 0 tonight → Item A auto-wires → future violations blocked at commit. It's not treating symptoms forever; it's the last manual fix before the automated guard takes over.

### Round 2

**Challenge:** Why didn't the Item A wire happen after run 49? check_project_invariants was fixed on June 5 (8db33df). The nightly scope was extended. Yet we're in June 10 and Check 10 is still not in pre-commit. What evidence suggests it will actually wire this time?

**Defend:** The nightly 2026-06-10 added Check 12 (timing-safe guard, 20 lines) to pre-commit — confirming the autonomous channel for pre-commit bash additions is active. The ONLY reason Check 10 hasn't wired since June 5 is that check_project_invariants has been exiting 1 (new violations in c8a0460 introduced June 10). With exit 0 restored tonight, there's no remaining blockers. Item A has been pending_autonomous with autonomous_executable:true since run 42.

### Round 3

**Challenge:** What if c8a0460 wasn't the only commit introducing new violations? Are there other em-dash regressions lurking?

**Defend:** `python3 scripts/check_project_invariants.py` shows exactly 3 violations, all in MemoryPanel.jsx:180 + AgentOS.jsx:197/224 — all from c8a0460. The script scans comprehensively; if there were others, they'd appear. This is a bounded, confirmed fix.

**Verdict: SURVIVES** — strongest mechanism linkage of any idea. Small fix → large downstream unlock (Check 10 → moratorium progress). Evidence tight. Autonomous channel confirmed via Check 12.

---

## Idea 2: Add tenant scope registration checklist to schema-discipline.md

### Round 1

**Challenge:** A doc checklist won't stop this. The developer (or Claude) writing a new service won't read the rule file carefully. Real prevention requires a programmatic check — a test that verifies every table referenced in services has an entry in `_TENANT_COLUMN_OVERRIDES`. That's the actual fix.

**Defend:** `schema-discipline.md` is path-scoped to `backend/**/*.py` — it auto-loads when Claude edits any Python backend file. The checklist is a forcing function in the session, not a document humans read separately. Additionally, `_TENANT_COLUMN_OVERRIDES` has 15 entries now; a pytest that validates all 15 tables are present would need to know what "all tables" means — which is harder to automate than a rule reminder. The rule file approach is practical and immediately effective.

### Round 2

**Challenge:** This idea was never recommended before. If the pattern occurred 3 times without the checklist, why would adding it now change behavior? Previous sessions read schema-discipline.md (it's path-scoped) and still missed the registration.

**Defend:** Previous sessions may not have explicitly known about `_TENANT_COLUMN_OVERRIDES` as a required step — it's buried in tenant_scope.py. Making it explicit in schema-discipline.md raises the salience. The c6805a5 bug was caught by nightly, not by the implementing session — suggesting the implementing session had no signal to look for this. A checklist item changes that.

### Round 3

**Challenge:** This is genuinely lower leverage than Idea 1. Idea 1 produces a tangible automated guard (Check 10) that catches real violations. Idea 2 adds a soft doc reminder. The gap between "automated guard" and "doc reminder" is large.

**Defend:** Both are valuable. But the debate is about choosing ONE winner. The checklist addresses a different class (tenant_scope registration) that Check 10 doesn't catch. However, the checklist alone won't be tested until the next new table — which might be weeks away. Impact is less immediate.

**Verdict: WEAKENED → Parking Lot** — valid prevention measure for a real recurring pattern. Loses to Idea 1 on immediacy and measurable downstream impact. Should be recommended in a future run when Agent OS development slows and new service creation is more deliberate.

---

## Idea 4: Cross-tenant isolation test for os_graph_memory

### Round 1

**Challenge:** Migration 133 RLS has been declared clean by nightly security analysis. If RLS is enforced at the DB layer, application-level cross-tenant tests are redundant. The real risk would be a future migration accidentally dropping RLS — but that would be caught by the pre-commit migration guard (Check 5).

**Defend:** Application-level tests catch bugs BEFORE the DB layer. The c6805a5 fix corrected `_TENANT_COLUMN_OVERRIDES` — but if the test suite for os_graph_memory had tested client_id filtering, the bug might have been caught even earlier, in CI rather than nightly. Check 5 catches duplicate migration numbers, not RLS drops. The isolation test fills a gap between mock-based CI and production RLS enforcement.

### Round 2

**Challenge:** Is this AUTONOMOUS-EXECUTABLE? The test needs to understand the os_graph_memory API well enough to construct a valid cross-tenant scenario. That requires reading 397 lines of service code. Nightly might not do this well autonomously.

**Defend:** The pattern is simple: `accumulate_from_turn(db, client_id="A", ...)`, then `graph_kb_entries(db, client_id="B", ...)` asserts empty result. The mock DB just needs to return correct fixtures. It's 20-30 lines of new test code, similar in complexity to the dispatch tests c6805a5 added.

### Round 3

**Challenge:** The dispatch tests (run 53 winner) were just added for os_action_dispatch.py. The graph memory tests were added with c8a0460 (284 tests). How much test coverage is enough before shipping new features? Adding more tests for the same feature competes with unblocking the moratorium exit path.

**Defend:** Valid point. The moratorium exit (via em-dash fix → Check 10 wire) is more impactful right now. The isolation test is valuable but not urgent given RLS is clean and nightly is monitoring. Better deferred to parking lot.

**Verdict: WEAKENED → Parking Lot** — real security value but lower urgency than Idea 1. Deferred until next Agent OS development sprint. Add to parking lot with ROI 2.1.

---

## Final Rankings

| Idea | Verdict | Notes |
|------|---------|-------|
| 1. Fix 3 em-dash violations → Item A | SURVIVES → WINNER | Autonomous, bounded fix, large downstream unlock |
| 2. Tenant scope checklist | WEAKENED → Parking Lot | Valid, lower immediacy, future run candidate |
| 4. Cross-tenant isolation test | WEAKENED → Parking Lot | Real value, RLS clean, defer until next Agent OS sprint |
| 3. Fix kb-autopopulate | WEAKENED → Parking Lot | 35d broken, path uncertain, low urgency |
| 5. Governance correction | Trivial → Phase 6 | Applied in Phase 6, not a debate-worthy idea |
