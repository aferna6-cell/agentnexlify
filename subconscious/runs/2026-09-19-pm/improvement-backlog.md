# Improvement Backlog — 2026-09-19-pm (Run 125)

## Active
- **Step 9G SKILL.md Fix**: Replace `gh workflow run kb-autopopulate.yml` with `mcp__github__actions_run_trigger` MCP call in nightly SKILL.md. KB stale 24+ days. Autonomous-executable mandate: PASSED (run 124 threshold, now run 125). Task prompt blocks this run; requires human approval.

## Parking Lot (survived debate but not chosen)

### Step 9E P0 Tier — 6th carry-forward (URGENT)
- AUTOPILOT_GH_TOKEN expires 2026-10-02 (13 days remaining)
- P0 threshold fires 2026-09-22 (3 DAYS from now)
- Action: add ≤10 days tier to Step 9E SKILL.md — file new GH issue with P0 label, separate from #399
- Autonomous-executable mandate PASSED (run 122). Blocked by task prompt for 6th consecutive run.
- **Human must act on this manually if autonomous execution remains blocked.**

### Dependabot Major-Version Triage GH Issue
- 5 Dependabot PRs open: react 18→19 (×2), vitest 4→5, mcp >=2.2.0
- Step 9J correctly skips major bumps but creates no tracking issue
- Action: file one GH triage issue listing all 5 PRs, label `dependencies + human-action-required`
- No autonomous-executable threshold; straightforward bonus action for next nightly

## Rejected This Run
None killed in debate. Ideas 1-2 both survived (1 chosen, 2 weakened to parking lot). Idea 3 weakened to parking lot.

## Deferred (not debated — parking lot from prior)

### AI Metering Trend Tracking (Step 9M Draft)
- 45 violations static across 5+ runs — no delta tracking exists
- Action: add Step 9M to SKILL.md: read `subconscious/state/ai-metering-trend.json`, compute delta vs yesterday, log +N/-N
- Impact: distinguishes stagnant from progressing; catches regressions immediately

### os_tool_executions.py God-Class Split Planning
- Service: 783L, Router: 436L (1219L combined), stable 7+ days (no commits since ~2026-08-30)
- 6th consecutive subconscious mention; god-class-splitter SKILL.md exists
- Action: read file, write split plan (4 concerns: execution, routing/dispatch, state/history, result-processing), file as GH issue comment
- Blocked by: no concrete plan yet; reading 783L file first required

## Questions for Next Run
1. Has human approved Step 9G fix? If yes, was it implemented? Check SKILL.md for `mcp__github__actions_run_trigger`.
2. Has AUTOPILOT_GH_TOKEN been rotated? P0 fires 2026-09-22 — 3 days away.
3. Did Step 9E P0 alert fire? If AUTOPILOT_GH_TOKEN still expires 2026-10-02 and run 126 is on/after 2026-09-22, the ≤10-day window has opened.
4. Any new Dependabot PRs? Are the 5 major-version bumps still unreviewed?
5. AI metering: still 45 violations or has run 126 seen delta?
