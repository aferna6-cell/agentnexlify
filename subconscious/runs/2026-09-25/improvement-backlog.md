# Improvement Backlog — Run 130 (2026-09-25)

## Active
- **Step 9G KB Failure Diagnostics** — poll kb-autopopulate.yml run status ~90s post-trigger; post to GH #403 on failure. Ends 15+ false-positive "TRIGGERED — SUCCESS" log lines. S effort, autonomous-executable. (Run 130 winner)

## Parking Lot (survived debate but not chosen)

- **Step 9E ELAPSED Auto-Issue Filing** — file GH issue when credential ELAPSED (days_remaining <= 0). Useful audit trail + GitHub notification path. Weakened: P0 tier already provides urgency signal; ELAPSED means automation already broken. Promote run 131 if Step 9G clears.
- **os_tool_executions.py God Class Split** — 783L file, CLAUDE.md Rule 9 threshold 600L, 7th parking lot mention. god-class-splitter + post-split-test-repair SKILLs ready. Requires human session (M effort). Promote when human-session window available.
- **GH #827 AI Metering Baseline Log** — add 3-line count of open billing+ai-ready issues to nightly log. Closes run_130_mandate item 6. No action threshold — logging only for trend baseline.
- **Step 9E Expiry State Persistence** — write ops/credential-state.json after P0 fires to suppress duplicate alerts within 24h. Reduces log noise. Promote post-token-rotation.

## Rejected This Run
- None killed in debate. All 3 top ideas either survived or were weakened (not killed).

## P0 Standing Items (human action required)
- **AUTOPILOT_GH_TOKEN expires 2026-10-02** — 6 days from today. GH #399. Rotate before nightly automation breaks.
- **Brain connector GitHub PAT** — expiry unknown, likely same. Rotate alongside AUTOPILOT_GH_TOKEN.
- **ANTHROPIC_API_KEY missing from GH Actions** — GH #403. Blocks KB autopopulate. Root cause of Step 9G false positives.

## Questions for Next Run
- Was Step 9G KB Failure Diagnostics implemented by nightly-2026-09-26? Check SKILL.md for mcp__github__actions_list in Step 9G.
- Did nightly log show "KB autopopulate: TRIGGERED — RUN FAILED" or "TRIGGERED+CONFIRMED"?
- Was AUTOPILOT_GH_TOKEN rotated before 2026-10-02? If yes: did Step 9G confirm successful KB run?
- GH #827 ai-metering: open count trending up or down?
