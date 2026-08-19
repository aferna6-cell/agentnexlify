# Improvement Backlog — 2026-08-19-pm (Run 108)

## This Run's Winner

**Step 9J — Dependabot Auto-Merge in Nightly** (AUTONOMOUS-EXECUTABLE, recommended this run)
- Category: workflow
- Effort: S (~50 lines bash block in SKILL.md)
- Impact: applies security patches within 24h of CI passing; eliminates 2-17d aging cycle
- Evidence: 6 PRs aging; morning digest flagged daily for 7+ days with zero human action

## Parking Lot (carry to run 109+)

### stale-autonomy-pr-closer SKILL.md (MEDIUM priority)
- Evidence: 7 open subconscious draft PRs (#626 9d, #613 11d, #611 12d, #606 14d, #648 13d, #653 10d, and more)
- Action: Create `.claude/skills/stale-autonomy-pr-closer/SKILL.md` — inspect draft PRs >10d from `subconscious/*` branches, close superseded ones with comment, label stale-but-valid ones for human review
- Trigger condition: pile >10 drafts OR oldest draft >30 days
- Category: workflow
- Effort: M (complex superseding detection; false-positive risk on PRs with live main commits)
- Run 109+ candidate

### PR #660 merge comment (LOW priority, one-time)
- scoring_config.py block_demo_role fix, 3d ai-ready, CI green
- Action: when human returns, point to #660 as mergeable
- Not a SKILL.md improvement — skip as subconscious winner

## Human-Only Blockers (not addressable by subconscious)

| Blocker | Age | Impact | Action |
|---------|-----|--------|--------|
| GH #399 — AUTOPILOT_GH_TOKEN expired | 42d+ | 30 ai-ready issues blocked, autopilot loop dead | Rotate token in Railway → GH Actions secret |
| GH #403 — ANTHROPIC_API_KEY missing in GH Actions | 42d+ | KB 27d stale, AI chat answers stale | Add secret (5-step guide in GH #403 bonus comment, run 107) |
| GH #394 — brain connector | 27d+ | Knowledge graph stale | Rotate PAT + SUPABASE_ACCESS_TOKEN |
| SUPABASE_ACCESS_TOKEN last_rotated | unknown | Step 9E can't alert on expiry | Fill in date from Supabase dashboard → ops/credential-rotation-schedule.md |
| PR #653 — appointment_briefs.py block_demo_role | 10d draft | Security gap open | Human review and merge |
| PR #660 — scoring_config.py block_demo_role | 3d ai-ready | Security gap open | Human merge (CI green) |

## Frozen Ideas

- ai_human_handoff: frozen per run 70 governance mandate

## Retired This Run

- Idea 4 (KB autopopulate local fallback): KILLED — mechanism already killed in run 104. Re-debate prohibited.
- Idea 5 (human-blocker consolidation GH issue): not structurally new; existing #399/#403 issues cover it.
