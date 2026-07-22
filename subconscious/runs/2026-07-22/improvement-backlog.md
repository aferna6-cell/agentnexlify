# Improvement Backlog — Run 100

## Active (filed this run)
| # | Title | Category | Effort | Status |
|---|-------|----------|--------|--------|
| 1 | Fix Agent OS plan gate coverage gap (10 routers) | code_health | M | GH issue to be filed → winning-concept.md |

## Parking lot (carry forward)
| # | Title | Category | Effort | Target run |
|---|-------|----------|--------|------------|
| P1 | Add Step 9G: Drive KB sync health to nightly review | workflow_efficiency | S | Run ~105 (Drive KB stabilization) |
| P2 | Extract mock DB helpers to shared conftest fixture | code_health | S | Run ~103 |
| P3 | calls.py god class split (H2 from audit) | code_health | L | Run ~104 |

## Killed this run
| # | Title | Kill reason |
|---|-------|-------------|
| K1 | Zapier plan_status verification gap | False positive — backend already enforces via bug #107 (2026-06-13). zapier/authentication.js comment confirms 402 for Free/cancelled tenants. |

## Bonus actions (not in backlog, executed inline)
- SUPABASE_ACCESS_TOKEN: Comment added on GH #399 (bundle with token rotation)
- GH #413: Comment added (REFERRAL_REWARD_ENABLED still not set, day 10+)

## Mandated checks — run 100 results
| Check | Result |
|-------|--------|
| Step 9F in SKILL.md | PASS — grep returns 6 hits, confirmed working in nightly 2026-07-22 |
| GH #399 (autopilot-issue-loop) | OPEN — day 18+, comment added (SUPABASE token bundled) |
| GH #413 (REFERRAL_REWARD_ENABLED) | OPEN — day 10+, comment added |
| Nightly 2026-07-21 | NOT FOUND — only three nightly files exist; 2026-07-22 nightly is current |
| Governance corrections (run 99) | VERIFIED — appointment_completion, BotHealthPage, AttributionPage confirmed via PR #475 |
