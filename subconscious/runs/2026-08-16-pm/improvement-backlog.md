# Improvement Backlog — 2026-08-16-pm

## Active
- Fix `scoring_config.py` block_demo_role — add router-level `dependencies=[Depends(block_demo_role)]` to close GH #661. Pattern: appointment_briefs.py run 106. Guide: route-security-guard-audit SKILL.md.

## Parking Lot (survived debate but not chosen)
- **Step 9I nightly paying-tenant zero-conversation alert** — WEAKENED this run (GH #403 blocks infrastructure). Revisit run 108 after ANTHROPIC_API_KEY is set in GH Actions.
- **ai_usage_guard in appointment_briefs.py** — WEAKENED (dict key verification needed before implementing). Check `reserve_ai_tokens()` signature vs `_get_current_tenant()` return shape. Implement after verification.
- **Update ops/credential-rotation-schedule.md AUTOPILOT_GH_TOKEN threshold 76d→45d** — XS doc fix, did not debate but low leverage vs Idea 1. Owner should update when rotating the token (GH #399).
- **Step 9H v2 subconscious PR pile alerter** — Valid, low priority. PR #653 already 12+ days draft. Good candidate for run 109 if #653 still open.

## Rejected This Run
None killed — all ideas survived debate to varying degrees. Two WEAKENED (timing, verification risk), one SURVIVES as winner.

## Questions for Next Run
1. Has GH #661 been merged? If yes, run the full route-security-guard-audit SKILL.md to find any remaining missing block_demo_role guards across all routers.
2. Has ANTHROPIC_API_KEY been added to GH Actions (GH #403)? If yes, Step 9I is unblocked for nightly addition.
3. Has AUTOPILOT_GH_TOKEN been rotated (GH #399)? If yes at 45+ days, Step 9E threshold change is validated.
4. Is PR #653 still draft? If open 19+ days, escalate Step 9H v2 to winning candidate.
5. What is `reserve_ai_tokens()` signature shape? Verify dict keys match `_get_current_tenant()` return before implementing ai_usage_guard in appointment_briefs.py.
