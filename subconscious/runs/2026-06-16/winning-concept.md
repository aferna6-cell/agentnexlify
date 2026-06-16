# Winning Concept — 2026-06-16

## Recommendation
Add pre-commit Check 13: wire `python3 scripts/check_project_invariants.py` into `scripts/hooks/pre-commit` as a FAIL-mode gate — a 6-line bash block, AUTONOMOUS-EXECUTABLE via nightly review.

## Why This, Why Now
check_project_invariants.py has been passing all 6 invariant checks since 3234597 (2026-06-13) — the first zero-blocker state in 46 days. The launch sprint (PRs #285-291, ~3000 lines in 3 days) shipped five new services (pay_gate.py, billing_usage.py, integration_key_vault.py, platform_support.py, billing_usage.py) without any of check_project_invariants' six checks enforced at pre-commit. Check 11 (billing guard, 022f4c58) and Check 12 (timing-safe, ca3ce68) both landed autonomously via nightly review — identical mechanism. Five of the six invariant classes (retired schema fields, retired plan names, widget byte-sync across 3 mirrors, em-dashes in JSX copy, direct SDK calls) are completely unguarded at commit time. Every future god-class split, router addition, or widget change now has a window to slip one of these bugs past review.

## Implementation Sketch
1. Open `scripts/hooks/pre-commit`
2. Find the end of the Check 12 block (~line 295)
3. Append this block:
```bash
# Check 13: project invariants gate
echo -n "Check 13: project invariants gate... "
if python3 scripts/check_project_invariants.py > /dev/null 2>&1; then
    echo "PASS"
else
    echo "FAIL"
    python3 scripts/check_project_invariants.py 2>&1 | grep -v "^PASS"
    echo "ERROR: Fix project invariant violations above before committing."
    exit 1
fi
```
4. Mark run 42 entry in governance.json as `implemented`
5. Mark run 56 entry as `superseded` (Check 2 already covers from __future__; run 56 proposed the same check under a different name)

**Autonomous path:** Update nightly-commit-review SKILL.md winning-concept inline patch section to include this block. Same mechanism as Check 11/12 autonomous wires.

## What This Replaces
Active direction from run 42 (2026-05-31, `pending_autonomous`, `autonomous_executable: true`). Also closes out run 56 (Check 13 from __future__ guard) which is superseded — Check 2 in pre-commit already guards from __future__ in router files.

## Governance Corrections (apply in Phase 6)
- **Run 55** (em-dash + from __future__ fix): `pending_autonomous` → `implemented` (3234597, 2026-06-13)
- **Run 57** (widget cp): `pending_autonomous` → `implemented` (3234597, 2026-06-13)
- **Run 56** (Check 13 from __future__ guard): `pending_autonomous` → `superseded` (Check 2 already covers this)
- **Runs 30/31/32/34** (AMOUNT_TO_PLAN GH #181): all `pending_approval` → `superseded_moot` (9bed342 repricing replaced AMOUNT_TO_PLAN entirely; old plan codes retired)
- **Run 51** (verify+merge PR #183): `pending_approval` → `superseded_moot` (PR #183 targeted old billing.py path; repricing made it moot)
- **runs_implemented**: 16 → 18 (runs 55 + 57 confirmed implemented)

## Confidence
HIGH — all six blocker categories cleared, mechanism proven (Check 11/12 autonomous), zero false positives on current codebase, AUTONOMOUS-EXECUTABLE, 6-line change.
