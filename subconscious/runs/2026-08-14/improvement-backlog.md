# Run 106 — Improvement Backlog (2026-08-14)

## Implemented this run
- [x] **appointment_briefs.py block_demo_role** — block_demo_role at router level, structural test in test_plan_gating_new_plans.py. Closes security gap (GH #643 partial).
- [x] **Step 9E threshold 76d → 45d** — nightly now warns 45 days before credential expiry (was 76). AUTOPILOT_GH_TOKEN at 41d will trigger next nightly.
- [x] **Governance reconciliation** — total_runs 102→106, last_run, run_107_mandate.

## Parking lot (carry-forward)

| Title | Cycles | Blocker | Priority |
|-------|--------|---------|----------|
| pr-backlog-triage SKILL.md | 2 | #399 (autopilot stalled) | MEDIUM |
| ai_usage_guard in appointment_briefs | 1 | Complexity (full tenant dict needed) | LOW-MEDIUM |
| Dependabot PR auto-merge comment | 1 | Human decision | LOW |

## Human-required (not subconscious's job)

| Issue | Action | Days Open |
|-------|--------|-----------|
| #399 | Rotate AUTOPILOT_GH_TOKEN in Railway | 41+ |
| #403 | Set ANTHROPIC_API_KEY + SUPABASE_ACCESS_TOKEN + VOYAGE_API_KEY in GitHub Secrets | ongoing |
| PR #653 | Merge (covers runs 102-106, including today's appointment_briefs fix) | 2 |
| #649/#629/#630/#631 | Merge dependabot PRs (safe patch/minor upgrades) | 9-10 |
| GH #643 | Close after PR #653 merges | 7 |

## Watch for (run 107 mandate)
1. Step 9E fires in tomorrow's nightly with AUTOPILOT_GH_TOKEN 42d alert
2. GH #643 closure after PR #653 merge
3. ai_usage_guard in appointment_brief.py service (reserve_ai_tokens at service layer)
4. PR #653 merge — delivers runs 102-106 to main
