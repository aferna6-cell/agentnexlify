# Improvement Backlog — Run 111 (2026-08-25-pm)

Ranked by ROI (impact × effort⁻¹). Winner excluded.

---

## BONUS A — Annual Plan Guard Audit

**Effort:** XS | **Category:** code_health | **ROI:** HIGH (revenue protection)

Check `ai_usage_guard.py` PLAN_BASELINE_TOKENS includes annual plan variants from 10acf83 revenue sprint. Annual subscribers at $1,199/yr must not get free-tier token limits. One grep + 10-min review. File GH issue if gap found.

---

## PARKING LOT A — Step 9D: GH Actions Dark Escalation

**Effort:** S | **Category:** operational | **Channel:** autonomous-executable (SKILL.md edit)

If GH Actions dark for >30 days AND no existing escalation issue → Step 9D files a summary issue documenting cascading blockers (Step 9J Dependabot queue, Step 9G KB autopopulate, Step 9D autopilot loop). GH Actions has been dark 36 days. Revisit run 112 if not yet acted on.

---

## PARKING LOT B — Step 9J: Comment on GH #500 after consecutive 0-merge nights

**Effort:** S | **Category:** operational | **Channel:** autonomous-executable (SKILL.md edit)

After N consecutive nights where Step 9J finds 0 eligible Dependabot PRs due to `mergeable_state: unknown` → add a comment to GH #500 with aging PR list and total wait time. Surfaces Dependabot cost within the right existing issue rather than creating duplicate tracking.

---

## KILLED — Step 9J: merge when GH Actions dark (lower threshold)

**Reason:** Policy decision — merging without CI passes constitutes a process override that requires explicit human authorization. HIGH merge risk for patch bumps. Removed from backlog; human decides case-by-case.

---

## WEAKENED → LATER — GH #669 block_demo_role middleware (PR #653)

Already tracked. PR #653 (13d, draft) proposes FastAPI middleware approach. No new subconscious signal adds value here. Resolution requires human review of PR #653.
