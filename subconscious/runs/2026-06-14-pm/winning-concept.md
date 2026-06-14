# Winning Concept — 2026-06-14-pm

**AUTONOMOUS-EXECUTABLE**

## Recommendation
Wire `scripts/check_project_invariants.py` into `scripts/hooks/pre-commit` as Check 10 — a 6-line bash addition that blocks commits with invariant violations (widget sync drift, banned column names, retired plan names, LLM wrapper bypass).

## Why This, Why Now
`3234597` (2026-06-13 launch-readiness sweep) cleared all three `check_project_invariants.py` blockers in a single commit: fixed widget sync drift, cleared 10 em-dash violations, and removed `from __future__ import annotations` from all router files. This is the first time in 55+ days that `python3 scripts/check_project_invariants.py` exits 0 cleanly. The pre-commit hook has Checks 1–9 but no Check 10 — a gap since run 8 (April 25). Two prior checks in the same class (Check 11 via 061582c, Check 12 via ca3ce68) were autonomously added by the nightly review cycle. Check 10 guards four invariants that NO other check covers: widget sync across all 3 copies, banned column names (`client_id` discipline that has caused 3+ production bugs), retired plan names, and LLM runtime wrapper compliance. Without it, the exact drift that required run 57's manual fix will silently recur on the next multilateral widget PR.

## Implementation Sketch

1. Read `scripts/hooks/pre-commit` to find the end of the Check 9 block (currently ends around line 244 with FAILURES counter logic).

2. Insert after the Check 9 block:
```bash
# CHECK 10: Project invariants (widget sync, column naming, plan names, LLM wrapper)
echo "--- CHECK 10: project invariants ---"
if python3 scripts/check_project_invariants.py 2>&1; then
  echo "PASS project invariants"
else
  echo "FAIL: project invariants — see above"
  FAILURES=$((FAILURES + 1))
fi
```

3. Verify locally: `bash scripts/hooks/pre-commit` — should complete with all PASS and exit 0. (Current state: all 6 invariants pass per this run's evidence gathering.)

4. Commit: `git add scripts/hooks/pre-commit && git commit -m "chore(pre-commit): wire check_project_invariants.py as Check 10 — seals invariant system (run 8 winner, 55d pending)"`

**AUTONOMOUS-EXECUTABLE:** Same class as Check 11 (22-line bash addition, 061582c autonomously applied) and Check 12 (20-line bash addition, ca3ce68 autonomously applied). Nightly review reads governance.json `pending_autonomous: true` + `autonomous_executable: true` flag and applies the bash addition directly. Zero code logic changed — pure bash file modification.

## What This Replaces
Run 57 winner (widget sync drift cp command) is IMPLEMENTED. Run 55 winner (from __future__ + em-dash fix) is IMPLEMENTED. Run 56 winner (Check 13 from __future__ guard) is SUPERSEDED — Check 2 already guards this, and Check 10 provides broader coverage. This run consolidates all three into a single permanent gate.

## Confidence
HIGH — evidence is concrete (`check_project_invariants.py` exits 0, pre-commit Checks 1-9 confirmed, autonomous channel for bash additions confirmed via Check 11+12), implementation is trivial (6 lines), blocking pattern is documented (widget drift recurs without guard), and the 55-day gap proves this is genuinely overdue.
