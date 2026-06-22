## Run 2026-06-22-pm — Debate Phase

**Top 3 ideas under review:**
1. Idea 1: Add Check 7 — Plan-Catalog Drift Guard to check_project_invariants.py
2. Idea 2: Activate AI-to-Human Handoff v1 (Explicit Trigger)
3. Idea 3: Create scripts/check_migration_coverage.py — Object-Level Migration Audit

**Moratorium constraint:** pending_approval count = 2 (email_sequences split + AI-to-Human Handoff from previous cycles). Winner MUST be AUTONOMOUS-EXECUTABLE or moratorium worsens.

---

### IDEA 1 — Add Check 7: Plan-Catalog Drift Guard

**CHALLENGE:**
- "check_project_invariants.py already has 6 checks. Are we just growing a monolith?"
- "plan_catalog.py is brand new (3d4c7db, 2026-06-22). Is it stable enough to import from in a pre-commit hook?"
- "test_plan_catalog_coverage.py in pytest already guards premium gates. What does a pre-commit check add?"
- "billing_reconciliation._PLAN_BASELINE_AI_TOKENS is an internal dict. What if someone restructures it?"

**DEFEND:**
- check_project_invariants.py is a collection of fast invariant checks, not a class — adding one more function doesn't create a god class. It's the right file for this check.
- plan_catalog.py exports a frozenset (`CURRENT_PAID_PLANS`). frozensets are stable by definition; importing them is safe. The file was committed to main (not a draft).
- pytest runs at CI time (minutes after push). Pre-commit runs at commit time (~10 seconds after `git commit`). The delta is 10x faster feedback. Every time a developer edits billing_reconciliation.py and forgets a plan, pre-commit catches it before CI ever runs. That's the value — same guard, earlier in the pipeline.
- `_PLAN_BASELINE_AI_TOKENS` is a module-level dict keyed by plan string. If someone restructures it, the test_plan_catalog_coverage.py pytest will also fail — the two guards reinforce each other. The implementation is a simple `assert plan in billing_reconciliation._PLAN_BASELINE_AI_TOKENS` — trivial to update if the dict name changes.

**VERDICT: SURVIVES. Challenge rebuffed on all four points. No significant weaknesses. AUTONOMOUS-EXECUTABLE.**

---

### IDEA 2 — Activate AI-to-Human Handoff v1

**CHALLENGE:**
- "This has been pending since Run 4 (65+ days). If it were urgent, wouldn't it have been implemented already?"
- "Adding to pending_approval under moratorium = making moratorium worse. moratorium_active=true, pending_approvals=2, max=2. This can't be winner."
- "widget_chat.py trigger detection is a pattern-match problem. What about false positives? 'I don't want a real solution' or 'give me a real answer' shouldn't trigger handoff."
- "GoHighLevel already has this. We're playing catch-up, not leading."

**DEFEND:**
- It IS urgent — customer-gaps.md rates it Critical, all 7 industries affected. The 65-day delay is governance friction (moratorium + context resets), not a product signal.
- Moratorium constraint is real: this idea CANNOT be winner this cycle. Even if it's the highest-value idea overall, adding a third pending_approval item violates governance.max_pending_approvals = 2. It goes to parking lot.
- False positive concern is valid but manageable — keyword list with phrase matching (not single-word), plus confidence threshold in the prompt before triggering. Addressable at implementation time.
- Playing catch-up to GoHighLevel on this specific feature closes a known gap. The risk of NOT shipping is losing trials to GHL's "AI Employee" demo.

**VERDICT: WEAKENED by moratorium constraint. Highest future priority once moratorium exits (first pending item approved). Moves to parking lot with elevated priority note.**

---

### IDEA 3 — Create scripts/check_migration_coverage.py

**CHALLENGE:**
- "This requires Supabase MCP access at script runtime. The check_project_invariants.py pattern uses pure Python — no external connections. A script that connects to Supabase is a different class of tool."
- "GH #263 false positive alarm already documented in migration-triage-2026-06-22.md. Developers now know it's a false alarm. Is automation still needed?"
- "How often does this panic actually fire? If it was a one-time event, the ROI on a full object-level audit script is questionable."
- "Parsing CREATE TABLE / ADD COLUMN / CREATE INDEX from 155+ SQL files has edge cases: comments, conditional DDL, multi-statement migrations."

**DEFEND:**
- The Supabase MCP dependency is a real concern. A script that requires live DB access can't run in pre-commit without credentials configured. It's more of a developer convenience tool than a CI gate. This is a weaker integration point than Check 7.
- The triage doc captures one incident (Jun-22). But GH #329 (migration 154 issue opened despite 154 already applied) suggests this is a recurring pattern, not a one-off. Two documented incidents = pattern.
- SQL parsing edge cases are non-trivial. A naive grep for CREATE TABLE misses: multi-line statements, comments, IF NOT EXISTS variants, EXECUTE statements in plpgsql. A robust parser requires either full SQL AST (overkill) or careful regex with known edge cases.
- The ROI case is valid but lower than Check 7. Check 7 prevents a known bug class (4 incidents) with ~15 lines. Idea 3 prevents a workflow pain (2 incidents) with ~150 lines + external dependency.

**VERDICT: WEAKENED by implementation complexity and Supabase dependency. Valid idea, lower leverage per line than Check 7. Moves to parking lot.**

---

### SYNTHESIS CALL

| Idea | Survives? | Moratorium-safe? | Pre-condition met? | Leverage |
|------|-----------|------------------|--------------------|----------|
| 1 — Check 7 | YES | YES (AUTONOMOUS-EXECUTABLE) | YES (Bonus A landed 2026-06-22) | HIGH (4 prior incidents, ~15 lines) |
| 2 — AI-to-Human Handoff | PARTIAL | NO (adds to pending_approval) | YES (delivery layer exists) | HIGHEST but blocked |
| 3 — Migration audit script | PARTIAL | YES (if implemented autonomously) | YES | MEDIUM (2 incidents, ~150+ lines) |

**WINNER: Idea 1 — Add Check 7 (Plan-Catalog Drift Guard).**

Reasons:
1. Only idea that is both moratorium-safe AND highest leverage per implementation cost.
2. Explicit pre-condition met by commits 57f2bb4 + 29ed1d4 (Bonus A from run 64 Bonus B).
3. Closes a recurring bug class (GH #81, #181, #292, #293) at the commit-time layer.
4. ~15 lines, pure Python, no external deps, drops into existing check_project_invariants.py pattern.
5. AUTONOMOUS-EXECUTABLE — nightly-commit-review can ship without human approval gate.
