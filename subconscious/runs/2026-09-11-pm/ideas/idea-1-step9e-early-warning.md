# Idea 1: Step 9E credential expiry escalation — lower trigger to 10 days before threshold (1st carry-forward)

**Evidence:**
- Run 119 winner: Step 9E early-warning escalation. NOT implemented (grep for 'days_remaining\|<= 10' in SKILL.md returns 0).
- AUTOPILOT_GH_TOKEN at 69d (threshold 76d) — 7 days to warning threshold. Current Step 9E only fires at >=76d.
- Winning concept: fire at <=10 days remaining (>=66d). At 69d, that threshold has already passed — alert should have fired 3 days ago.
- 3 consecutive nightlies logged warning; zero GH issue filed; zero human action.
- Token expires 2026-10-02. Loop death if not rotated.

**Action:**
Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block:
Change threshold from `days_since_rotation >= 76` to `days_remaining = threshold_days - days_since_rotation` and fire GH issue when `days_remaining <= 10`.
Full implementation sketch in run 119 winning-concept.md (dedup guard: search by credential name, add comment to existing issue rather than create duplicate).

**Impact:** AUTOPILOT_GH_TOKEN alert fires in next nightly cycle. Brain PAT same. Loop death from credential expiry prevented. Dedup guard ensures GH #399 gets a comment rather than a new duplicate issue.

**Category:** workflow_efficiency

**Effort:** XS (single block edit in SKILL.md)

**Confidence:** HIGH — 1st carry-forward, exact sketch exists, mechanism proven (Steps 9F/9G/9I/9J/9K all same pattern).
