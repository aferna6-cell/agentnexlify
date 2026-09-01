# Idea 4 — Gmail Connector Auth Pattern KB Article

**Category:** workflow_efficiency
**Effort:** XS

## Evidence
- 5-commit Gmail sprint created knowledge of derived key pattern, 401 retry, send-only flag
- No KB article on connector auth patterns exists
- KB last run 2026-08-26 — healthy (5d, within 7d threshold)

## Weakness
Lower leverage than Step 9L which addresses the same underlying gap at scale.
KB article helps humans who read it; Step 9L catches future connector code automatically.
Parking lot: can be bundled with 9L implementation as bonus action.

## Verdict
**WEAKENED** → parking lot. Worth doing as bonus when 9L is implemented, not as primary winner.
