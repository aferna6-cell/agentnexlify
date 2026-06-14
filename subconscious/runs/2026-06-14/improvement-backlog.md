# Improvement Backlog — 2026-06-14

## Active
- Wire `check_project_invariants.py` into pre-commit as Check 10 + Check 13 (from __future__ bash guard) in same commit — AUTONOMOUS-EXECUTABLE, run 22 item finally unblocked by first-ever exits 0

## Parking Lot (survived debate but not chosen)
- **Governance mega-correction** (Idea 3): Apply in Phase 6 this run. Mark runs 55/57 → implemented (3234597). Run 51 → implemented (billing.py fixed). Recount true pending to determine moratorium lift.
- **email_sequences.py god-class split** (Idea 4, run 35/41): All prerequisites now met (GH #181 fixed, both skills ready). Promote to winner once moratorium lift confirmed via governance correction.
- **Cross-tenant isolation tests for os_graph_memory** (parking lot ROI 2.1): No new evidence. Defer to next Agent OS sprint.
- **Zapier API key plan_status enforcement** (GH #107, parking lot ROI 2.5): Security issue tracked, route via issue-to-pr-loop.
- **WordPress plugin tests** (Idea 5): PHPUnit infra missing; low urgency day 1. Promote after plugin ships to first customer.
- **IntegrationHealthDashboard.jsx split** (633L, just crossed 600L threshold): Stabilize first, then split. Check at next architecture audit.
- **kb-autopopulate.sh fix** (parking lot ROI 1.8, 35d+ broken): Replace agent-browser calls.
- **Fix email_sequences N+1 queries** (GH #112, parking lot ROI 2.3): After email_sequences split.

## Rejected This Run
- **Idea 2 as standalone winner** (Check 13 only): Subsumed by Idea 1 — Check 10 wires Python invariant script which covers from __future__ via AST. Check 13 added as Bonus A in same commit.
- **Idea 4 as winner** (email_sequences split, moratorium active): WEAKENED — pending count uncertain until governance correction; moratorium max_pending_approvals=2 applies.

## Governance Corrections Applied This Run
- **Run 55** (from __future__ + em-dashes): pending_autonomous → implemented (3234597, 2026-06-13)
- **Run 57** (widget drift cp): pending_autonomous → implemented (3234597, 2026-06-13)
- **Run 51** (PR #183 billing.py): pending_approval → implemented (3234597 fixed billing.py directly, 15000+25000 confirmed present)
- **runs_implemented**: 16 → 19
- **Oldest pending_approval**: run 4 (AI-to-Human Handoff, 59 days) — still blocking moratorium exit

## Questions for Next Run
1. Was Check 10 wired? (grep "Check 10" scripts/hooks/pre-commit — should match)
2. Was Check 13 wired? (grep "Check 13\|from __future__" scripts/hooks/pre-commit)
3. After governance correction, what is true pending_approval count? Does it meet max_pending_approvals=2?
4. Is moratorium now eligible to lift? (pending_approval ≤ 2 after corrections?)
5. If moratorium lifts: recommend email_sequences.py split (run 41, all prerequisites met)?
