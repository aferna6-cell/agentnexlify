# Debate Log — Run 121 (2026-09-16-pm)

Top 3 ideas debated: Step 9E (Idea 1), Step 9G (Idea 2), AI Metering (Idea 3)

---

## Idea 1: Step 9E Credential Expiry Escalation — 2nd Carry-Forward

### Advocate
AUTOPILOT_GH_TOKEN expires in 16 days. It has been at or near the threshold for 5+ days across 3 nightly runs. Each nightly logged a warning. None triggered human action because no GH issue was filed — there was no email, no assignee, no audit trail. This is a broken notification loop, and the loop failing to notify is precisely the bug Step 9E was designed to fix.

The fix is proven: add `days_remaining <= 10` threshold check, search for existing open issue with `credential-rotation` label + credential name, comment on GH #399 if found, else create new issue. PR #874 already exists with this implementation sketch.

This is the 2nd carry-forward. By established precedent (Steps 9F/9G/9I/9J/9K), the 3rd carry-forward triggers autonomous implementation at run 122. Run 122 fires tomorrow. The autonomous path is clear.

If AUTOPILOT_GH_TOKEN expires unrotated, the nightly-commit-review loop, the issue-to-pr-loop, and the autonomous engineering loop all die. That's a hard system failure with a 16-day deadline.

### Objection 1: Step 9E won't matter if the human rotates the token today
The token rotation is independent of Step 9E. Even if the human rotates AUTOPILOT_GH_TOKEN today (as morning digest recommends), Brain PAT also expires ~2026-10-02, SUPABASE_ACCESS_TOKEN state is unknown, and the underlying broken notification mechanism (no GH issue = no email) persists for ALL future credential expirations. Step 9E is the systemic fix. Token rotation is the immediate fix. Both are needed.

### Response to Objection 1
Sustained — Step 9E is still needed even after manual rotation. This objection strengthens the recommendation rather than weakening it.

### Objection 2: This is a 2nd carry-forward. Why didn't the human implement it from run 120's recommendation?
Unclear. PR #874 exists as DRAFT. The morning digest explicitly flagged it as "Undraft and merge to unblock autonomous escalation at run 122." The human may be intentionally deferring to let the autonomous-executable mechanism fire. Or PR #874 may be the implementation plan waiting for review.

Either way: the recommendation stands. If the human wants automation to handle it, run 122 is the autonomous-executable trigger. If the human wants to implement manually, PR #874 is ready.

### Objection 3: At 74d with a 76d threshold, the token hasn't crossed yet — isn't this premature?
The `days_remaining <= 10` threshold we're proposing fires at 66+ days since rotation (threshold 76d − 10d buffer = trigger at 66d). AUTOPILOT_GH_TOKEN is at 74d, well past 66d. So under the NEW Step 9E logic, this token already crossed the threshold 8 days ago. We've already missed 8 days of warning. The fix is overdue.

### Verdict: SURVIVES — WINNER

---

## Idea 2: Step 9G MCP Trigger Fix

### Advocate
Step 9G is broken in every nightly session. gh CLI is unavailable in the cloud execution environment. KB is 21 days stale (threshold 7 days). Brain connector is 55 days stale (threshold 14 days). Both are downstream of Step 9G being unable to trigger the GH Actions workflow.

The fix is straightforward: replace `gh workflow run kb-autopopulate.yml` with `mcp__github__actions_run_trigger`. This is an XS-effort, high-value change. Run 120 "parked" this idea pending verification; run 121 should advance it to at least a firm recommendation or a parking-lot verdict.

### Objection 1: Is `mcp__github__actions_run_trigger` available in nightly sessions?
Unknown. The nightly session runs as a scheduled Claude Code session with the same MCP configuration as this session. The GitHub MCP server is listed in the deferred tools. But whether `actions_run_trigger` is specifically available, and whether the AUTOPILOT_GH_TOKEN has `workflow:write` scope needed to trigger it, is unverified.

### Response to Objection 1
This is a legitimate blocker. The recommendation cannot be "implement this" until we verify: (a) `mcp__github__actions_run_trigger` is in the GitHub MCP server, (b) it works in nightly sessions, (c) `kb-autopopulate.yml` has `workflow_dispatch` trigger. Without verification, implementing this could replace a visible failure ("gh CLI not available") with a silent failure (tool call fails silently).

### Objection 2: Even if Step 9G fired successfully, the KB autopopulate is blocked by GH #403 — missing `ANTHROPIC_API_KEY` in GH Actions secrets
This is a deeper blocker. Step 9G triggers the GH Actions workflow. The workflow needs `ANTHROPIC_API_KEY`. GH #403 is a human-action-required blocker for setting that secret. Step 9G working correctly would trigger the workflow, which would then fail silently due to missing `ANTHROPIC_API_KEY`.

So Step 9G's inability to trigger is masking a deeper problem: even if Step 9G worked, the workflow would fail. Fixing Step 9G alone doesn't unstale the KB.

### Objection 3: This is the 3rd time this idea has appeared in the parking lot
Run 118: Step 9G mentioned as broken. Run 120: "parked (unverified)". Run 121: still unverified. The right action is to do the verification now, not park again.

### Response to Objection 3
Agreed. But the constraint is: this is a RECOMMEND-only run. Verification would require calling `mcp__github__actions_run_trigger` in a test context and reading `kb-autopopulate.yml` — that's implementation territory. The correct recommendation is: "verify mcp__github__actions_run_trigger availability in nightly context before implementing Step 9G fix."

### Verdict: SURVIVES AS PARKING LOT — Not the winner, but escalate from "unverified" to "needs pre-verification checklist." Do not block Step 9E for this.

---

## Idea 3: AI Metering Hotpath Triage — GH #875

### Advocate
40 production call sites calling the Claude API without `ai_usage_guard` check. Any free-plan tenant can burn unbounded tokens. GH #875 is filed and labeled `ai-ready`. This is a real cost risk. The subconscious should track it.

### Objection 1: Issue is 0 days old and already labeled ai-ready
GH #875 was filed by the nightly run earlier today. It's labeled `ai-ready` and `billing`. The issue-to-pr-loop polls ai-ready issues every 15 minutes. Subconscious recommending this same issue as the run 121 winner would be redundant — the automation already has a path forward.

### Objection 2: Morning digest already flagged it as priority #2
The morning digest explicitly listed this as Priority 2 for today. It also noted "needs a human to confirm scope first." If the human is reading the morning digest, this is already visible. Subconscious amplifying the same signal this run adds no new information.

### Objection 3: The issue-to-pr-loop should handle this without subconscious involvement
The `ai-ready` label exists precisely to feed the issue-to-pr-loop. The correct escalation path is: human confirms scope → loop picks up → opens PR. Subconscious adding a 2nd recommendation channel for the same issue creates confusion about which automation owns it.

### Verdict: ELIMINATED — Redundant with GH #875 + morning digest + issue-to-pr-loop. No subconscious carry-forward needed.

---

## Final Selection

| Idea | Verdict |
|------|---------|
| Step 9E 2nd carry-forward | WINNER — RECOMMEND |
| Step 9G MCP fix | PARKING LOT — Needs pre-verification checklist before advancing |
| AI Metering #875 | ELIMINATED — Already handled via issue-to-pr-loop |
| React 19 gate in 9J | Not debated — Low urgency |
| os_tool_executions.py split | Not debated — Stability window broken |
