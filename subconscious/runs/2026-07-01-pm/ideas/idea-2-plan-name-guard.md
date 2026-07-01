# Idea 2 — Plan-Name Guard: Add `foundation`/`operations` to check_project_invariants.py

**Category:** code_health / operational  
**Effort:** XS  
**Type:** AUTONOMOUS-EXECUTABLE  
**Score:** 7/10

## Problem

`scripts/check_project_invariants.py` (Check 5) validates that retired plan names `foundation` and `operations` do not appear in the codebase. But the check runs as a post-hoc scan only — it does not prevent regressions during development.

CLAUDE.md says: "Retired names, never use: `foundation`, `operations`." Bug-patterns.md and stripe_service.py establish `chatbot` / `agent_os` as the only live plan names. 

The invariant check currently passes (confirmed run 76 check_project_invariants.py output — all 5 non-widget checks PASS). This means the guard is working. But there is no pre-commit hook equivalent for plan name use.

## Proposal

Add a pre-commit hook snippet that greps for retired plan names in staged Python + JSX files:

```bash
# In scripts/hooks/pre-commit.d/check-plan-names.sh
RETIRED="foundation|operations"
if git diff --cached --name-only | grep -E "\.(py|jsx|js|ts|tsx)$" | xargs grep -lE "\"($RETIRED)\"" 2>/dev/null; then
    echo "ERROR: staged file contains retired plan name (foundation/operations)"
    exit 1
fi
```

Alternatively: add to the existing `check_project_invariants.py` as a git-hook-callable check (already invoked in pre-push).

## Why Interesting

- XS effort
- AUTONOMOUS-EXECUTABLE — no schema, no frontend, no migration
- Compounding: retired plan names are the exact class of bug that re-surfaces years later (e.g., new engineer sees old code)
- Pairs with existing Check 5 in invariants script

## Why Not Top Pick

- Current guard already catches this (check_project_invariants runs pre-push)
- No new incident motivating urgency
- Adding a pre-commit layer is nice-to-have, not security-blocking
- Zapier mandate overrides all candidates this run
