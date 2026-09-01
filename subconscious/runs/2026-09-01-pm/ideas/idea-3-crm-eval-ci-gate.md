# Idea 3 — Wire Agent-Service CRM Eval to CI as Required Gate

**Category:** agent_performance
**Effort:** S

## Evidence
- PR #726 (commit 81507fa): added crm-decision-path-v1.json eval dataset + run-crm-decision-path-eval.ts
- M8 sprint: most active codebase area (20+ commits in 3 days)
- No confirmation eval is registered in .github/workflows/ — not verified

## Weakness
Evidence that eval is MISSING from CI is unconfirmed without reading workflows.
M8 sprint pace makes adding a new required CI gate risky — could break active feature work.
Evidence base insufficient for conviction.

## Verdict
**WEAKENED** — evidence unconfirmed; wrong timing during active M8 sprint.
Parking lot: revisit when M8 sprint settles (0-commit stability on agent-service files).
