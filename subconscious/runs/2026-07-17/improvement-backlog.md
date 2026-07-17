# Improvement Backlog — 2026-07-17 (Run 97)

## Active

- **Step 9F: KB Autopopulate Staleness Check** — Add bash block to nightly-commit-review SKILL.md checking knowledge-base/log.md last-entry timestamp; if >7 days stale, log result + comment on GH #403. Guard wraps all failure paths (missing file, parse error, token expiry). AUTONOMOUS-EXECUTABLE via nightly SKILL.md-edit channel. Implementation sketch in winning-concept.md.

## Parking Lot (survived debate, not chosen this run)

- **appointment_completion.py** — Auto-complete past-confirmed appointments (end_time past 30-min cutoff), fire `appointment_completed` event unlocking review requests, rebook prompts, aftercare automations. GH #454 filed (ai-ready) — queued for issue-to-pr-loop when GH #399 resolved. Full sketch in subconscious/runs/2026-07-16-pm/winning-concept.md. DO NOT re-debate as subconscious winner until GH #399 resolved. Mechanism for autonomous execution: issue-to-pr-loop only.
- **notify_common.py failure-mode tests** — Verify `dispatch_owner_alert` returns error signal on `safe_send_email` failure; verify `IdempotencyGuard` blocks duplicate dispatch; verify `fetch_owner_alert_config → None` path. Run 98 candidate AFTER confirming 12 new tests from nightly-2026-07-17 don't already cover these paths.
- **BotHealthPage.jsx** — Frontend dashboard for admin_loop_health endpoint (/api/admin/loop-health). Endpoint ships 5 vitals. GH issue filed (Bonus B, run 96). Pattern: AdminFunnelPage. L-effort. No ai-ready label until GH #399 resolved.

## Bonus Actions Executed This Run

*(none — pure synthesis + artifact run, no GH actions taken; bonus actions from run 96 still active)*

## Rejected This Run

*(none new — os_opportunities referral_activation rule killed in run 96 remains dead)*

## Mechanism Insight (Run 97 — Carry Forward to All Future Runs)

**appointment_completion.py cannot be a subconscious winner until GH #399 resolved.** Root cause confirmed over 3 consecutive runs (95, 96, 97): nightly-commit-review is a bug-fix system — it runs `auto_fix_commit()` which patches existing files for LOW-risk bugs. It does NOT create new service files from subconscious winning-concept.md. The execution path for new service files is: issue-to-pr-loop (requires AUTOPILOT_GH_TOKEN in GH #399) OR human interactive session. Do NOT re-recommend appointment_completion.py as subconscious winner until one of these is unblocked. GH #454 (ai-ready) is the correct queue.

## Questions for Run 98

1. Step 9F block present in `.claude/skills/nightly-commit-review/SKILL.md`? (check grep output)
2. First nightly execution — "Step 9F:" line in nightly log?
3. KB still stale: GH #403 new Step 9F comment?
4. GH #454 (appointment_completion.py) has ai-ready label + full implementation sketch?
5. GH #399 resolved? (Day 16+)
6. GH #413 REFERRAL_REWARD_ENABLED=1 set? (Day 27+)
7. notify_common.py: read 12 new tests — do they cover dispatch_owner_alert failure modes?
