# Idea 1: Step 9E — Days Remaining Display + Dedup Reliability (2nd carry-forward)

**Category:** workflow_efficiency / operational
**Effort:** XS
**Confidence:** HIGH
**Carry-forward:** 2nd (autonomous-executable at run 122 = 3rd consecutive miss)

## Evidence
- AUTOPILOT_GH_TOKEN last rotated 2026-07-04. As of 2026-09-12 = 70 days elapsed.
- Current Step 9E fires at >= 76 days → fires in ~6 days (2026-09-18).
- Proposed improvement: fire at days_remaining <= 10 (= 66+ days) → would have fired 4 days ago.
- Current SKILL.md Step 9E block has GH issue search (lines 290-298) but threshold is ">=76 days" — log message line 300.
- Run 120 winning-concept confirmed `days_remaining` and `<= 10` NOT in SKILL.md. Step 9E block fires too late and doesn't display days remaining.
- AUTOPILOT_GH_TOKEN expiry: ~2026-10-02 (20 days). If not rotated, autonomous loop dies.
- Dedup risk: GH #399 (existing AUTOPILOT_GH_TOKEN issue) may lack `credential-rotation` label → Step 9E creates duplicate issue instead of commenting on #399.

## Action
Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block:
1. Change threshold from `>= 76` to `days_remaining = (interval_days - days_since_rotation)` where alert fires when `days_remaining <= 14` (2 weeks advance).
2. Display `days_remaining` in log line and GH comment body.
3. When searching for existing issues: also search by title containing credential name (not just label), so GH #399 is found even without `credential-rotation` label.
4. If found: comment with `days_remaining` countdown. If not found: create issue.

## Impact
- Fires 14 days before threshold (vs current 0 days = fires AT threshold).
- Visible countdown in GH issues.
- Prevents duplicate issue creation for AUTOPILOT_GH_TOKEN (GH #399 already exists).
- Escalation: if run 122 also misses, auto-implement via SKILL.md direct edit.
