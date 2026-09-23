# Improvement Backlog — 2026-09-23 (Run 127)

## Active

- **Step 9E P0 Tier:** Add 10-day credential expiry escalation branch to Step 9E in nightly-commit-review SKILL.md. AUTOPILOT_GH_TOKEN expires 2026-10-02 (9 days). Autonomous-executable since run 122. 7th carry.

## Parking Lot (survived debate but not chosen)

- **Pre-commit hook for new unguarded AI call sites** — Blocks commits adding new AI calls without metering guard. Depends on check_ai_metering.py `--staged-only` mode reliability (untested). Design clarity needed (git hooks vs `.claude/settings.json`). Revisit once false-positive rate verified.

- **Step 9J ordering fix** — Move Dependabot processing before Steps 9F/9G to prevent token-budget skip of 17/19 PRs. Tradeoff unclear (deprioritizes security/KB steps). Needs investigation: is token budget truly the bottleneck or is it detection?

- **GH #892 CI network isolation** — Add `pytest-socket` + conftest fixture to prevent CI safety tests from escaping to network. Human-actioned or issue-to-pr-loop (GH #399 required). Not subconscious-autonomous.

- **os_tool_executions.py god class split** — GH #881 (tech-debt, ai-ready, 783 lines). Stable since f22ef04. ai-ready queue needs GH #399 resolved. Human-driven implementation.

## Rejected This Run

- None (no ideas killed outright — all ideas from this run have valid evidence)

## Questions for Next Run

1. Was AUTOPILOT_GH_TOKEN rotated? (Check ops/credential-rotation-schedule.md `last_rotated` for AUTOPILOT_GH_TOKEN and GH #893 status.)
2. Did tonight's nightly fire Step 9E with P0 tier? If Step 9E P0 tier implemented, did dedup-skip correctly reference GH #893?
3. Are fresh Dependabot PRs (#885–#891) merged by Step 9J? Count: how many processed vs skipped?
4. GH #827 (45 unguarded AI sites): has the count grown since check_ai_metering.py was added? Trend determines urgency of pre-commit hook.
