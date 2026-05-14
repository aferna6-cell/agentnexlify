# Nightly Commit Review — 2026-05-14

**Reviewer:** nightly-commit-review agent  
**Window:** Last 24 hours (since 2026-05-13 ~06:00 UTC)  
**Commits reviewed:** 1  
**Auto-fixes applied:** 0  
**New GH issues filed:** 0  

---

## Commits Triaged

### 1. `52847b1` — ops: nightly-commit-review 2026-05-13
**Risk:** LOW  
**Files:** `ops/routines/logs/nightly-commit-review-2026-05-13.md` (63 lines added)  
**Assessment:** Pure ops log. No code, no schema, no API surface. Previous nightly review output confirming 1 LOW commit triaged, 0 auto-fixes, and GH #107 (Zapier plan_status) as pre-existing HIGH issue. No bugs introduced.

---

## Environment Checks

| Check | Result |
|-------|--------|
| Widget copies in sync (widget/ ↔ frontend/public/widget/) | PASS — byte-identical (md5: 997eb698) |
| Widget copies in sync (widget/ ↔ landing-page-v2/widget/) | PASS — byte-identical (md5: 997eb698) |
| `scripts/check-widget-sync.sh` present | MISSING — moratorium item, human approval required |

---

## Issues Found

None. Only commit in the 24-hour window is the previous nightly ops log.

---

## Pre-Existing Tracked Issues (Informational)

### [EXISTING GH #107] Zapier API key plan_status not enforced — HIGH
**File:** `backend/routers/zapier.py:86-134` (`_get_api_key_client`)  
**Status:** Open 13+ days. Requires human approval before any fix (auth/payments path). Route via issue-to-pr-loop when approved.

---

## Subconscious Moratorium Status (Informational)

Moratorium remains active after run 16 (last run 2026-05-11). 4 pending items.

| Run | Item | Days Pending | Effort | Status |
|-----|------|-------------|--------|--------|
| 4 | AI-to-Human Handoff v1 | 27+ | M (1.5-2 days) | URGENT — requires sprint |
| 7 | Widget 3-Copy Sync Guard | 19 | S (~15 min) | Awaiting human approval |
| 8 | Wire check_project_invariants.py to pre-commit | 18 | S (~5 min) | Awaiting human approval |
| 14 | Wire lead qualifier golden eval to CI | 8 | S (~20 min) | Awaiting human approval |

Widget copies currently byte-identical across all 3 locations — no production incident today, but the sync guard remains absent.

---

## Summary

No issues found in today's commit window. Single commit is ops-only (prior nightly log). Widget copies byte-identical across all 3 locations (PASS × 3). Pre-existing GH #107 remains the only open issue from nightly backlog. Moratorium at 4 pending items, oldest 27 days.

**Recommended human action:** Run 3 S-effort moratorium items (runs 7 + 8 + 14, ~40 min total) to exit moratorium, then route GH #107 to issue-to-pr-loop for auth-safe fix.
