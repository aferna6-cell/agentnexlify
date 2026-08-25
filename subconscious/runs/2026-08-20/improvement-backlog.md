# Improvement Backlog — Run 2026-08-20

## Winner (implementing this run)

| ID | Title | Category | Effort | Status |
|----|-------|----------|--------|--------|
| step-9j | Dependabot auto-merge in nightly SKILL.md | operational | S | WINNER — autonomous-executable |

## Parking Lot (strong, not this run)

| ID | Title | Category | Effort | Reason parked | Tracking |
|----|-------|----------|--------|---------------|---------|
| middleware-demo-guard | Middleware-level block_demo_role FastAPI guard | code_health | M | Human approval required; different timescale than S autonomous winner. GH #669 is tracking vehicle (filed 2026-08-20 by Step 9I). | GH #669 |
| step-9k | Stale autonomy PR closer in nightly (Step 9K) | workflow | S | Valid but lower urgency than Step 9J mandate. 5 draft PRs aging 10-19 days. | skill-discovery-2026-08-17.md |
| gh403-supabase-diagnostic | GH #403 SUPABASE_URL diagnostic comment | operational | XS | Bonus action for this run. KB 28d stale, second blocker may exist after run 107 ANTHROPIC_API_KEY comment had no effect. | GH #403 |

## Killed (this cycle)

| ID | Title | Reason killed |
|----|-------|---------------|
| gh399-day40-escalation | GH #399 Day-40 cost-of-delay comment | Non-structural. 4+ prior escalations same mechanism, zero human response. Pattern of failure. Recycled as bonus action if run time allows. |

## Frozen Ideas (permanent)

| ID | Reason |
|----|--------|
| ai_human_handoff | Frozen by governance since run 21. Complex product feature requiring active product sprint. Not subconscious territory. |

## Open Blockers (for human action)

| Issue | Description | Days stale | Impact |
|-------|-------------|-----------|--------|
| GH #399 | AUTOPILOT_GH_TOKEN expired | Day 40+ | 30 ai-ready issues blocked in issue-to-pr-loop |
| GH #403 | ANTHROPIC_API_KEY (+ possibly SUPABASE_URL) missing in GH Actions | 28d KB stale | KB autopopulate dark; AI chat on stale knowledge |
| GH #669 | 97/97 routers missing Depends(block_demo_role) | filed 2026-08-20 | Demo tenants can mutate data through 95 router files |
