# Improvement Backlog — 2026-08-19

## This Run's Winner

**Step 9I — Nightly demo-role security sweep** (AUTONOMOUS-EXECUTABLE, implemented this run)
- Category: code_health
- Effort: S (~50 lines bash block in SKILL.md)
- Impact: catches block_demo_role misses within 24h of introduction
- Closes: entire class of recurring security bug (GH #643, GH #661 = 2 instances in 6 days)

## Parking Lot (carry to run 108+)

### Step 9J — Dependabot auto-merge in nightly (HIGH priority)
- Evidence: 6 Dependabot PRs aging 1-15d (#629/#630/#631 15d, #649 unknown, #665/#666 1d)
- Action: Add Step 9J bash block to nightly — list open Dependabot PRs via mcp__github__, for each with CI green + no requested changes, merge via gh pr merge --squash
- Category: workflow
- Effort: S (~40 lines)
- Run 108 candidate if Step 9I lands cleanly

### stale-autonomy-pr-closer SKILL.md (MEDIUM priority)
- Evidence: 4 autonomy draft PRs 8-26d old (#575 26d, #626 16d, #648 8d, #653 10d)
- Action: Create .claude/skills/stale-autonomy-pr-closer/SKILL.md — inspect draft PRs >10d, close superseded ones with comment, label stale-but-valid ones for human review
- Category: workflow
- Effort: M (complex superseding detection logic)
- Note: requires careful dedup. Defer until PR pile >8 drafts.
- Run 109+ candidate

## Human-Only Blockers (not addressable by subconscious)

| Blocker | Age | Impact | Action |
|---------|-----|--------|--------|
| GH #399 — AUTOPILOT_GH_TOKEN expired | 39d+ | 30 ai-ready issues blocked, autopilot loop dead | Rotate token in Railway → GH Actions secret |
| GH #403 — ANTHROPIC_API_KEY missing in GH Actions | 39d+ | KB 27d stale, AI chat answers stale | Add secret (exact steps in GH #403 bonus comment this run) |
| GH #394 — brain connector | 25d+ | Knowledge graph stale | Rotate PAT + SUPABASE_ACCESS_TOKEN |
| SUPABASE_ACCESS_TOKEN last_rotated | unknown | Step 9E can't alert on expiry | Fill in date from Supabase dashboard → ops/credential-rotation-schedule.md |
| PR #653 — appointment_briefs.py block_demo_role | 10d draft | Security gap open | Human review and merge |
| PR #660 — scoring_config.py block_demo_role | 3d ai-ready | Security gap open | Human merge (CI green) |

## Frozen Ideas

- ai_human_handoff: frozen per run 70 governance mandate

## Retired this run

None — no ideas were debated to death.
