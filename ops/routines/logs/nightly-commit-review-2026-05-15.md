# Nightly Commit Review — 2026-05-15

**Reviewer:** nightly-commit-review agent  
**Window:** Last 24 hours (since 2026-05-14 ~06:00 UTC)  
**Commits reviewed:** 1  
**Auto-fixes applied:** 0  
**New GH issues filed:** 0  

---

## Commits Triaged

### 1. `e508c73` — ops: nightly-commit-review 2026-05-14
**Risk:** LOW  
**Files:** `ops/routines/logs/nightly-commit-review-2026-05-14.md` (63 lines added)  
**Assessment:** Pure ops log. No code, no schema, no API surface. Previous nightly review confirming 1 LOW commit triaged, 0 auto-fixes, 0 new issues. No bugs introduced.

---

## Environment Checks

| Check | Result |
|-------|--------|
| Widget copies in sync (widget/ ↔ frontend/public/widget/) | PASS — byte-identical (md5: 997eb698) |
| Widget copies in sync (widget/ ↔ landing-page-v2/widget/) | PASS — byte-identical (md5: 997eb698) |
| `.claude/subconscious/` directory present | ABSENT — not present in this environment; moratorium state tracked in prior logs only |

---

## Issues Found

None. Only commit in the 24-hour window is the previous nightly ops log.

---

## Pre-Existing Tracked Issues (Informational)

### [EXISTING GH #107] Zapier API key plan_status not enforced — HIGH
**File:** `backend/routers/zapier.py:86-134` (`_get_api_key_client`)  
**Status:** Open 14+ days. Requires human approval before any fix (auth/payments path). Route via issue-to-pr-loop when approved.

---

## Subconscious Moratorium Status (Informational)

Moratorium items carried from prior log (subconscious dir absent in this environment). Last known state: 4 pending items, moratorium active after run 16 (2026-05-11).

| Run | Item | Est. Age | Effort | Status |
|-----|------|----------|--------|--------|
| 4 | AI-to-Human Handoff v1 | 28+ days | M (1.5-2 days) | URGENT — requires sprint |
| 7 | Widget 3-Copy Sync Guard | 20 days | S (~15 min) | Awaiting human approval |
| 8 | Wire check_project_invariants.py to pre-commit | 19 days | S (~5 min) | Awaiting human approval |
| 14 | Wire lead qualifier golden eval to CI | 9 days | S (~20 min) | Awaiting human approval |

Widget copies currently byte-identical across all 3 locations — no production incident, but sync guard remains absent.

---

## Summary

No issues in today's commit window. Single commit is ops-only (prior nightly log). Widget byte-identical across all 3 locations (PASS × 3). GH #107 remains the only open backlog issue; requires human approval to proceed. Moratorium at 4 pending items, oldest 28+ days.

**Recommended human action:** Approve 3 S-effort moratorium items (runs 7 + 8 + 14, ~40 min total) to exit moratorium, then route GH #107 to issue-to-pr-loop.
