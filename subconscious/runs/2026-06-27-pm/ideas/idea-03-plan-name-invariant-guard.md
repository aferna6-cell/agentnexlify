# Idea 03: Plan-Name Invariant Guard — Add foundation + operations to Check 7

**Category:** code_health / operational
**Effort:** XS (10 minutes — 2 string additions to check_project_invariants.py)
**ROI:** 2.0 (prevents regression, low effort)
**Age:** Bonus A from runs 65/66/67/68/69 — never promoted to winner
**Autonomous:** AUTONOMOUS-EXECUTABLE (bash guard addition, same class as prior pre-commit additions)

## Evidence

- check_project_invariants.py Check 7 currently guards against `foundation` and `operations` plan names in plan-related code
- Wait — actually need to verify. The Bonus A from runs 65-69 says "add foundation+operations to invariant #3" (plan-name guard). But Check 7 might already have them.
- CLAUDE.md: "Retired names, never use: `foundation`, `operations`"
- `backend/services/stripe_service.py` + `ai_usage_guard.PLAN_BASELINE_TOKENS` are canonical plan definitions
- Bonus A from run 69: "Plan-name guard Check 7 expansion (add foundation+operations to invariant #3, sequenced after drift resolves)"

## What

Add `foundation` and `operations` to the retired plan names list in `check_project_invariants.py` Check 7 (or invariant #3). Pre-commit guard would then reject any code that introduces these retired names.

Current Check 7 presumably checks for a subset of retired names. Adding two more strings prevents the regression class seen in GH #292/#293 (chatbot/agent_os missing from plan dicts).

## Risk

- Must verify current state of Check 7 before adding (avoid duplicate entries)
- XS effort — minimal blast radius
- Sequencing: requires check_project_invariants.py to exit 0 first (widget drift must be fixed)
- Widget drift is NOW RETIRED from subconscious — human has the fix command
- Once drift is fixed, this becomes unblocked

## Debate Position

**WEAK candidate for run 70 winner slot** — sequencing blocked until widget drift is fixed (human action required first). XS effort, but cannot execute autonomously until pre-commit unblocks.

**Verdict:** WEAKENED → Bonus A. Include in improvement-backlog.md as first item after widget drift fix. AUTONOMOUS-EXECUTABLE once check exits 0.
