# Improvement Backlog — Run 115

Updated: 2026-08-28-pm

---

## Active (implementing or recently implemented)

| Title | Run | Status | Notes |
|-------|-----|--------|-------|
| Step 9L dead service detector | 115 | RECOMMENDED THIS RUN | first rec → human approve next cycle |
| Step 9J allow merge on unknown | 114 | implemented | dirty/blocked skip, unknown proceeds |
| Step 9K stale PR closer | 110 | pending_human (PR #683) | draft PR open 3d |
| Step 9J major-version safety gate | 110 | implemented | major bumps skip to human review |
| Step 9I demo-role sweep | 107 | implemented | nightly sweeps, files issues |
| Pre-commit block_demo_role hook | 111 | pending_human (PR #683) | 4 runs since recommendation |
| git push in subconscious Phase 8 | 105 | implemented | cloud container durability |

---

## Parking Lot

| Title | Evidence | When to promote |
|-------|----------|----------------|
| Step 9K stale PR closer (direct SKILL.md) | PR #683 supersedes for now | After PR #683 merges |
| GH #399 Day 60+ escalation | 60d open, AUTOPILOT_GH_TOKEN expired | Bonus action this run |
| GH #687 voice addon double-billing | billing risk:medium | When GH #399 resolved; ai-ready loop executes |
| Step 9J nightly verification | no data yet | Run 116: check nightly-2026-08-28 result |
| Middleware block_demo_role FastAPI guard | M-effort | After GH #399 resolved |

---

## Rejected / Frozen

| Title | Reason |
|-------|--------|
| ai_human_handoff | frozen — rejected 3+ times |
| widget drift (autonomous fix) | retired run 70 — FORBIDDEN paths, human-only task |
| Step 9J @dependabot rebase trigger | superseded by run 114 simpler fix (allow merge on unknown) |

---

## Open Questions

1. GH #399 (AUTOPILOT_GH_TOKEN expired) — Day 60. Pattern: 8+ escalation comments, zero action. Is the actual blocker a permissions problem that requires an org admin, not the dev? Consider filing as blocker to the ai-ready loop directly in GitHub Projects.
2. PR #683 (subconscious/run-110) — draft for 3d. Contains Step 9K + pre-commit hook. What is blocking human review of this PR? Is it awareness or prioritization?
3. agent_escalation.py — 88 LOC, 0 router callers. Orphaned service? Was it supposed to be wired in somewhere? Check git blame for intent.
