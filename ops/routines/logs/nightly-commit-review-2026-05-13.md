# Nightly Commit Review — 2026-05-13

**Reviewer:** nightly-commit-review agent  
**Window:** Last 24 hours (since 2026-05-12 ~06:00 UTC)  
**Commits reviewed:** 1  
**Auto-fixes applied:** 0  
**New GH issues filed:** 0  

---

## Commits Triaged

### 1. `2ae7c93` — ops: nightly-commit-review 2026-05-12
**Risk:** LOW  
**Files:** `ops/routines/logs/nightly-commit-review-2026-05-12.md` (74 lines added)  
**Assessment:** Pure ops log. No code, no schema, no API surface. Previous nightly review output recording 2 LOW commits and confirming GH #107 (Zapier plan_status) as a pre-existing HIGH issue. No bugs introduced.

---

## Environment Checks

| Check | Result |
|-------|--------|
| Widget copies in sync (widget/ ↔ frontend/public/widget/) | PASS — byte-identical |
| Widget copies in sync (widget/ ↔ landing-page-v2/widget/) | PASS — byte-identical |
| `scripts/check-widget-sync.sh` present | MISSING — moratorium item, human approval required |

---

## Issues Found

None. Only commit in the 24-hour window is the previous nightly ops log.

---

## Pre-Existing Tracked Issues (Informational)

### [EXISTING GH #107] Zapier API key plan_status not enforced — HIGH
**File:** `backend/routers/zapier.py:86-134` (`_get_api_key_client`)  
**Status:** Open 12+ days. Route via issue-to-pr-loop. No auto-fix (auth/payments path).

---

## Subconscious Moratorium Status (Informational)

Moratorium remains active after run 16 (last run 2026-05-11). No pending items implemented.

| Run | Item | Days Pending | Effort | Status |
|-----|------|-------------|--------|--------|
| 4 | AI-to-Human Handoff v1 | 26+ | M (1.5-2 days) | URGENT — requires sprint |
| 7 | Widget 3-Copy Sync Guard | 18 | S (~15 min) | Awaiting human approval |
| 8 | Wire check_project_invariants.py to pre-commit | 17 | S (~5 min) | Awaiting human approval |
| 14 | Wire lead qualifier golden eval to CI | 7 | S (~20 min) | Awaiting human approval |

Widget copies currently byte-identical across all 3 locations — no production incident today, but the sync guard is still missing.

---

## Summary

No issues found in today's commit window. Single commit is ops-only (prior nightly log). Widget copies byte-identical (PASS × 2). Pre-existing GH #107 remains the only open issue from the nightly review backlog. Moratorium at 4 pending items, oldest 26 days.

**Recommended human action:** Run 3 S-effort moratorium items (runs 7 + 8 + 14, ~40 min total) to exit moratorium. Then prioritize GH #107 via issue-to-pr-loop.
