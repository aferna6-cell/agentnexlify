# Improvement Backlog — 2026-08-17

## Active
- Add `git push origin HEAD` to subconscious SKILL.md Phase 8 to prevent orphaned commits in ephemeral cloud containers

## Parking Lot (survived debate but not chosen this run)
- **Step 9I: Add nightly demo-role security sweep** — Add a step to nightly-commit-review SKILL.md that greps `backend/routers/` for mutating endpoints missing `block_demo_role`. Depends on route-security-guard-audit SKILL.md being verified first (implemented this run). Propose in run 106.
- **GH #403 targeted comment** — Post exact secret name and setup instructions to unblock KB autopopulate. Tactical but valid. Low effort. Can be done by any run.

## Implemented This Run (autonomous-executable)
- **route-security-guard-audit SKILL.md** — 3rd carry-forward mandated direct implementation per run 105 governance mandate. Created at `.claude/skills/route-security-guard-audit/SKILL.md`.

## Rejected This Run
- **AI-to-human handoff GH issue** — Pattern frozen in governance.json (`ai_human_handoff`). GH #399 blocker (AUTOPILOT_GH_TOKEN expired) prevents issue-to-pr-loop from actioning it. Even scoped-down spike version not chosen due to blocker.

## Questions for Next Run (run 106)
1. Did `git push origin HEAD` land? Check origin/main for commits after e177031.
2. Is route-security-guard-audit SKILL.md in origin? Verify `.claude/skills/route-security-guard-audit/SKILL.md` exists in GitHub.
3. Did KB autopopulate run post-2026-07-23? Check knowledge-base/log.md for new entry. GH #403 (ANTHROPIC_API_KEY) still blocking?
4. GH #661 (scoring_config.py block_demo_role): has a PR been filed?
5. SUPABASE_ACCESS_TOKEN: has human filled in last_rotated date in ops/credential-rotation-schedule.md?
6. Propose Step 9I (nightly demo-role sweep) if route-security-guard-audit SKILL.md verified working.
