# Winning Concept — Run 2026-09-25 (Run 130)

## Title
Step 9G KB Failure Diagnostics — poll run status post-trigger + GH #403 comment on failure

## Category
workflow_efficiency

## Effort
S (15-20 lines in SKILL.md, 1 additional mcp tool call, ~90s added to nightly runtime)

## Problem
Step 9G in nightly-commit-review SKILL.md triggers kb-autopopulate.yml via mcp__github__actions_run_trigger, waits 30s passively, then logs "KB autopopulate: TRIGGERED — SUCCESS" unconditionally. ANTHROPIC_API_KEY missing from GH Actions (GH #403) causes every kb-autopopulate.yml run to fail silently. Result: 15+ consecutive nightly runs report false-positive success while KB stagnates 30+ days stale (last compiled 2026-08-26).

## Mechanism
In SKILL.md Step 9G, after triggering the workflow:
1. Wait 90 seconds (kb-autopopulate.yml runs ~30s; buffer for GH Actions queue)
2. Call mcp__github__actions_list (or equivalent) to find the most recent kb-autopopulate.yml run
3. Check run conclusion: completed/success vs failure/cancelled
4. If failure: post targeted comment to GH #403 with run date + conclusion ("ANTHROPIC_API_KEY likely missing from GH Actions secrets — see this run's failure log")
5. Log "KB autopopulate: TRIGGERED+CONFIRMED (run succeeded)" or "KB autopopulate: TRIGGERED — RUN FAILED (GH #403 notified)"
6. Guard: only post to GH #403 if no Step-9G-diagnostic comment within last 24h (prevent spam)

## Exact Change
In `.claude/skills/nightly-commit-review/SKILL.md`, Step 9G section:

**Replace:**
```
- Wait 30 seconds
- Log: "KB autopopulate: TRIGGERED — SUCCESS"
```

**With:**
```
- Wait 90 seconds (allow run to complete)
- Call mcp__github__actions_list with repo="aferna6-cell/agentnexlify", workflow_id="kb-autopopulate.yml", perPage=1
- Check run status/conclusion
- If succeeded: log "KB autopopulate: TRIGGERED+CONFIRMED"
- If failed/cancelled: log "KB autopopulate: TRIGGERED — RUN FAILED" + post comment to GH #403
  (guard: skip comment if Step-9G-diagnostic comment already posted in last 24h)
- If still in_progress after 90s: log "KB autopopulate: TRIGGERED — status in_progress, check GH Actions"
```

## Evidence
- KB last compiled 2026-08-26 (30 days stale as of 2026-09-25)
- Step 9G triggering via mcp__github__actions_run_trigger since run 101 (2026-08-06) confirmed
- GH #403 confirms ANTHROPIC_API_KEY missing from GH Actions — every kb-autopopulate.yml run fails
- Nightly logs since ~2026-08-26 show "TRIGGERED — SUCCESS" = 15+ false positives
- Step 9J cleared by nightly-2026-09-25 (parking lot condition for Step 9G explicitly met in run 129)
- Run 129 debate verdict: "Step 9G KB Failure Diagnostics: SURVIVES MODERATE (deferred)" — waiting for Step 9J clearance

## Autonomous-Executable Status
**ELIGIBLE** — SKILL.md edit with S risk. nightly-commit-review autonomous-executable channel applies. 1st carry-forward (run 130 = eligible for implementation on the next nightly cycle).

## Expected Impact
- Ends 15+ consecutive false-positive "success" log lines per nightly
- Every nightly run produces honest diagnostic: succeeded or failed
- When run fails: GH #403 receives actionable comment with run date (human sees clear notification path)
- When ANTHROPIC_API_KEY is rotated by human: Step 9G will immediately log confirmed success — KB recovery detectable
- No change to total nightly runtime beyond ~90s additional wait + 1-2 tool calls

## P0 Note (carry-forward from prior runs)
AUTOPILOT_GH_TOKEN expires 2026-10-02 — **6 days from today**. Human action required before nightly automation breaks. GH #399 open. This subconscious recommendation is independent of token rotation — implement both.

## NOT implementing this run
Recommendation only. Implementation via nightly-commit-review autonomous-executable channel on next nightly cycle.
