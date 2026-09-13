# Idea 1: Step 9E — Days Remaining Display + Credential-Identity Dedup

**Category:** workflow_efficiency / operational
**Effort:** XS
**Confidence:** HIGH
**Carry-forward:** 2nd

## Evidence
- AUTOPILOT_GH_TOKEN last rotated 2026-07-04. As of 2026-09-12 = 70 days elapsed.
- Current Step 9E fires at `days_since_rotation >= 76`, which is already the 14-day warning point for a 90-day interval.
- The defect is not that the current threshold fires later than a 14-day warning. The defect is that Step 9E does not compute/display `days_remaining` and deduplicates globally by the `credential-rotation` label instead of by credential identity.
- AUTOPILOT_GH_TOKEN next due date is ~2026-10-02. Existing issue #399 should be reused for that credential.

## Action
Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block:
1. Compute `days_remaining = interval_days - days_since_rotation` and use `days_remaining <= 14` as the readable equivalent of the current threshold.
2. Display credential name and `days_remaining` in the nightly log and GitHub comment.
3. Search existing open human-action/ops/credential-rotation issues by credential identity, not merely by label or exact proposed title. Reuse #399 for AUTOPILOT_GH_TOKEN when still open.
4. If no credential-specific tracker exists, create one. Keep unknown-date credentials on a separate unknown-state path without fabricated countdown math.

## Impact
- Preserves the existing 14-day warning window while making urgency explicit.
- Prevents cross-credential dedup and duplicate tracker creation.
- Makes the Step 9E output auditable and consistent with the issue title.
