# Improvement Backlog — 2026-06-08-pm (Run 52)

## Active
- **Add Check 12 — agent-service timing-safe guard to pre-commit (AUTONOMOUS-EXECUTABLE, WARNING mode)** [run 52 winner]

## Parking Lot (survived debate but not chosen)

- **Merge PR #209** — close GH #206 timing attack (5 min, Bonus A). Already #1 in morning digest. Human action today.
- **Merge PR #200** — unblock Items A+B autonomous chain tonight (5 min, Bonus B). PR open 3 days. Cascades: Check 10 + widget sync guard auto-execute 2:37 AM.
- **Agent OS booking agent eval harness** — `backend/tests/evals/test_booking_agent_golden.py` + 10 golden cases for slot extraction. lead-qualifier-eval.yml pattern ready. Promote after moratorium exits. (ROI 2.2 estimated, M-effort ~2h)
- **KB VOYAGE_API_KEY cron fix** — add graceful fallback in kb-autopopulate.sh + add key to Railway cron env. 34-day stale gap. (S-effort, operational)

## Rejected This Run
- None killed in debate (Idea 2 and Idea 1 WEAKENED to parking lot / bonus actions, not killed)

## Questions for Next Run
1. Was Check 12 wired autonomously tonight? (`grep "Check 12" scripts/hooks/pre-commit`)
2. Were PRs #209/#200/#183 merged? (security, autonomous chain, billing) — these 3 together drop moratorium pending by ~3+
3. Did Items A+B execute in tonight's nightly (2:37 AM) — check for Check 10 in pre-commit + scripts/check-widget-sync.sh presence?
4. Is the agent-service `_orchestrator.ts` (414L) approaching god-class threshold? Should a TypeScript god-class-splitter be scoped?
5. Has VOYAGE_API_KEY been added to Railway cron? KB stale day 37+ if not.
