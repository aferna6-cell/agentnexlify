# Improvement Backlog — 2026-08-18

## Status: Winner
**Step 9I — nightly demo-role security sweep in SKILL.md**  
Status: PENDING_HUMAN_APPROVAL (carry-forward 1 of 2)  
Escalates to: AUTONOMOUS-EXECUTABLE at run 108  
Evidence: GH #643 + #661 (same class, 6 days apart); nightly-2026-08-18 confirmed logic correct  
Action: Edit `.claude/skills/nightly-commit-review/SKILL.md`, add Step 9I block after Step 9H

---

## Status: Parking Lot (run 108 candidate)
**`dependabot-merge-runner` skill**  
Proposed by: skill-discovery-2026-08-17  
Evidence: 4 Dependabot PRs aging 7-14 days (CI green, safe to merge) — morning digest flags daily  
Blocker: None (no GH #399 dependency)  
Action: Create `.claude/skills/dependabot-merge-runner/SKILL.md`  
Promote if: Step 9I approved/implemented before run 108

---

## Status: Parking Lot (run 108 candidate)
**`stale-autonomy-pr-closer` skill**  
Proposed by: skill-discovery-2026-08-17  
Evidence: 5 stale draft PRs aging 15-20+ days  
Timing risk: GH #399 resolution would cause PR merge cascade, changing situation  
Action: Defer until after #399 resolved or Step 9I + dependabot-merge-runner clear the queue

---

## Status: Killed This Run
**GH #399 escalation comment**  
Reason: Mechanism exhausted (38+ days, same message repeated in every nightly log). Human knows. Information not the bottleneck. Killed for this run.

---

## Active Carry-Forward Items (not actionable without human)
| Item | Blocker | Age |
|------|---------|-----|
| #399 AUTOPILOT_GH_TOKEN expired | Human must rotate token | 38d+ |
| #403 ANTHROPIC_API_KEY missing in GH Actions | Human must add secret | 38d+ |
| #394 brain connector | PAT + SUPABASE rotation | 24d+ |
| #643 appointment_briefs block_demo_role | PR #653 needs merge | 9d+ |
| #661 scoring_config block_demo_role | PR #660 ai-ready | 3d |
| SUPABASE_ACCESS_TOKEN last_rotated date | Human must fill in `ops/credential-rotation-schedule.md` | Unknown |
