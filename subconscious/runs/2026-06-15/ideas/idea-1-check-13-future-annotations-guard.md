### Idea 1: Add pre-commit Check 13 — `from __future__ import annotations` guard (AUTONOMOUS-EXECUTABLE)

**Evidence:** Run 56 winner (2026-06-12) remains unimplemented after 3 days. Pre-commit ends at Check 12 (agent-service timing-safe guard). `grep -c "from __future__ import annotations"` on backend/routers/*.py returns 0 actual violations — previous runs 55+57 fixed them — but Check 13 is still absent, leaving every future router split unprotected. 100% recurrence rate: PR #238 introduced 3 new violations within 24h of run 55 targeting channels_instagram.py. 98 router files exist; each potential split is a live exposure window without the guard.

**Action:** Add ~10-line bash block to scripts/hooks/pre-commit after Check 12. Pattern: `grep -rn "from __future__ import annotations" $(git diff --cached --name-only | grep "^backend/.*\.py$")`. FAIL (not WARNING) if found. Bypass: `# ok-future-annotations` comment.

**Impact:** Blocks the bug class that 422'd ALL Instagram endpoints (CLAUDE.md Critical Invariant #5). Autonomous-executable by nightly. Zero human approval needed. Closes run 56 pending_autonomous.

**Category:** code_health
