# Idea 5 — Triage and Close Stale Subconscious Draft PRs

**Category:** operational
**Effort:** S

## Evidence
- Step 9K (nightly-2026-09-01): found 3 stale subconscious PRs (30-35d)
- Approaching comment threshold (≥5 stale or any >60d)
- PRs accumulate nightly run artifacts with no human review

## Weakness
Too vague without listing specific PR numbers + their content.
Closing PRs is irreversible — needs human confirmation.
Step 9K already auto-escalates when threshold is crossed; this idea duplicates that.
Better as bonus action in the nightly run than as a subconscious recommendation.

## Verdict
**WEAKENED** → bonus action. Step 9K handles the escalation path. Human should review + close PRs manually.
