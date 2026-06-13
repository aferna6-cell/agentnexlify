# Winning Concept — 2026-06-13-pm

**AUTONOMOUS-EXECUTABLE**

## Recommendation
Wire `check_project_invariants.py` into `scripts/hooks/pre-commit` as Check 10, completing the
50-day-pending run 8 winner now that the script exits 0 for the first time.

## Why This, Why Now
PR #257 (3234597, 2026-06-13) cleared all three invariant failures — widget sync drift, em-dash
violations, and from __future__ annotations — as part of the launch-readiness P0 sweep. For the
first time since 2026-04-25, `python3 scripts/check_project_invariants.py` exits 0 with "All
project invariants passed." The only blocker that kept Check 10 from wiring (exits 1) is now
gone. The launch-readiness sprint is running at 50 commits/7 days — exactly the velocity where
invariant regressions are most likely. Wiring Check 10 NOW prevents em-dash re-introduction,
widget drift, from __future__ slip, and retired field usage from sliding back in under commit
pressure. Check 11 (billing guard, 061582c) and Check 12 (timing-safe guard, ca3ce68) prove the
nightly autonomous channel reliably wires bash additions to pre-commit. This is the same class.

## Implementation Sketch

```bash
# scripts/hooks/pre-commit — add after line ~246 (end of CHECK 9 block):
# CHECK 10: Project invariants (naming, widget sync, em-dash, future-annotations)
echo ""
echo "Running check_project_invariants.py..."
if python3 scripts/check_project_invariants.py; then
  echo "CHECK 10 PASS: all project invariants met"
else
  echo "CHECK 10 FAIL: project invariants violated — see output above"
  echo "Run: python3 scripts/check_project_invariants.py for details"
  exit 1
fi
```

Steps:
1. Read `scripts/hooks/pre-commit` to find the end of CHECK 9 block (confirm line ~246)
2. Insert the CHECK 10 block after CHECK 9
3. Test: run `git diff HEAD~1 HEAD | head -5 && bash scripts/hooks/pre-commit` to confirm PASS
4. Commit: `git add scripts/hooks/pre-commit && git commit -m "ops: add Check 10 — project
   invariants gate to pre-commit (wires check_project_invariants.py)"`
5. Update governance.json: run 8 status `subsumed_in_sprint → implemented`; run 22 status
   `pending_autonomous → superseded`

**AUTONOMOUS-EXECUTABLE**: Nightly review reads governance.json, sees this as pending_autonomous
(run 8 active_directions entry). Nightly SKILL.md scope covers bash additions to pre-commit
(4226ef4). Same class as Check 11 (061582c) and Check 12 (ca3ce68) — both wired autonomously.

## What This Replaces
Closes run 8 winner (2026-04-25, 50 days). Supersedes run 22 which also targeted Check 10.
Complements — does not replace — Check 2 (from __future__ grep in pre-commit): Check 2 is a
fast grep guard; Check 10 uses AST for reliability plus checks 5 additional invariant classes
that Check 2 doesn't cover.

## Governance Corrections (applied this run)
- Run 57 (widget sync drift): `pending_autonomous → implemented` (PR #257 3234597 confirmed
  `landing-page-v2/widget/agentnexlify-widget.js` updated +202 lines)
- Run 55 (from __future__ + em-dashes): `pending_autonomous → implemented` (PR #257 cleared
  both; check_project_invariants.py exits 0 confirms)
- Run 56 (Check 13 from __future__ guard): `pending_autonomous → partially_implemented`
  (CHECK 2 in pre-commit was tightened in PR #257 "anchor __future__ grep"; separate Check 13
  block not added, but AST-level protection now in check_project_invariants.py)
- Run 51 (PR #183 billing fix): `pending_approval → implemented` (billing.py:263 confirmed has
  15000→autopilot + 25000→professional since PR #255 ca718ab)

## Confidence
HIGH — condition cleared by PR #257 (concrete, verifiable), autonomous execution channel proven
by 2 prior pre-commit bash additions (Checks 11+12), 3-line implementation identical to those,
50-day item with no remaining blockers.
