# Idea 2: Add Plan-Name Invariant Guard to check_project_invariants.py

**Category**: code_health  
**Confidence**: HIGH  
**Effort**: S (~15 min, 1 Python addition)  
**Autonomous**: YES (AUTONOMOUS-EXECUTABLE) — sequenced after Idea 1  
**Status**: Was Bonus B in runs 60-64. Now unblocked by GH #292/#293 implementation (2026-06-23).

## What is missing

check_project_invariants.py runs 6 invariant checks. It does NOT have a check for plan name usage. Since the 2026-06-16 repricing to 2-plan model (chatbot/$19.99, agent_os/$99.99), incorrect plan names can creep in silently.

GH #292/#293 (implemented 2026-06-23) fixed specific missing plan names in 3 service files. But without a guard in check_project_invariants.py, any future code can re-introduce retired plan names (`foundation`, `operations`, `growth`, `autopilot`, `professional`) without detection.

## What to add

**Check 7** in `scripts/check_project_invariants.py`:

Scan `backend/` Python files for retired plan name strings used in plan-comparison logic:
- Retired: `foundation`, `operations` (never use per CLAUDE.md)
- Grandfathered but no longer active in new code: `growth`, `autopilot`, `professional`
- Current: `chatbot`, `agent_os`, `free`

Pattern: grep for `== "foundation"`, `== "operations"`, `!= "operations"`, etc. in Python service files where plan comparison happens.

Also: verify `_UNLIMITED_PLANS`, `_ALLOWED_PLANS`, `_PLAN_BASELINE_AI_TOKENS` contain both `chatbot` and `agent_os`. Cross-reference against `backend/services/stripe_service.py` canonical plan list.

## Sequencing constraint

**BLOCKED until Idea 1 lands.** check_project_invariants.py currently exits 1. Adding a new check before fixing the existing failures would:
1. Mask which failures are new vs. existing
2. Make the pre-commit output confusing
3. Violate the invariant that the script is the source of truth for clean state

Once Idea 1 delivers and check_project_invariants.py exits 0, this becomes the next highest-priority autonomous candidate.

## Why this matters

GH #292/#293 took 8 days and 6 subconscious run cycles to get fixed. A guard would have:
- Caught the gap at commit time (2026-06-16, day of repricing)
- Prevented the alternating mandate mechanism from consuming runs 59-64
- Protected against future repricing events

## Parking lot precedent

Was "Bonus B" in runs 60-64 winning-concepts. Implementation sketch already written (subconscious/runs/2026-06-20-pm/winning-concept.md §Bonus B).
