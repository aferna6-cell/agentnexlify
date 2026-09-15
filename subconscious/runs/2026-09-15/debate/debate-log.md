# Debate Log — Run 2026-09-15 (Run 121)

Top 3 ideas debated by impact. Each challenged then defended. Verdict: SURVIVES, WEAKENED, or KILLED.

---

## Idea 1: Step 9E — days_remaining ≤10 threshold + GH issue filing (2nd carry-forward)

### Challenge

1. **Threshold change unwarranted?** Step 9E already fires at 76 days (14-day warning before 90-day expiry). AUTOPILOT_GH_TOKEN is at day 73 — fires in 3 days under existing logic. Why change the threshold now?

2. **Duplicate GH issues.** GH #399 already tracks AUTOPILOT_GH_TOKEN rotation and has been open 73+ days. Filing another credential-rotation issue creates duplicates that confuse the GH issue list.

3. **Is this the highest leverage thing?** Step 9G is completely broken (no-op in all cloud sessions). KB is 20d stale because of this. Fixing Step 9G has compounding daily value that surpasses a one-time credential alert.

4. **Human has already seen GH #399 for 73 days and not acted.** A new GH issue won't change behavior. The bottleneck is human attention, not lack of issues.

### Defend

1. **Threshold matters for GH issue filing.** The 76-day log entry fires in 3 days but doesn't create a GH issue. The `days_remaining <= 10` threshold (day 66+) would have fired 7 days ago AND filed a comment on GH #399. That comment triggers a GitHub email notification — something a log entry in a markdown file does not. The distinction: log line vs. GH notification.

2. **Dedup guard explicitly handles GH #399.** The winning-concept.md specifies: "Dedup: search by label 'credential-rotation' + credential name slug. GH #399 is the existing AUTOPILOT_GH_TOKEN rotation issue — comment on it rather than creating duplicate." No new issue created; existing issue gets a fresh comment with current days_remaining count. Email triggered.

3. **This is the 2nd carry-forward. Governance binds.** Run 119 proposed it; run 120 was 1st carry-forward. Per governance precedent (Steps 9F, 9G, 9I, 9J, 9K, 9L — all auto-implemented on 3rd carry-forward), run 122 fires autonomous implementation. Recommending again at run 121 is the correct escalation path. Step 9G fix is a separate Idea 2 with its own uncertainty.

4. **AUTOPILOT_GH_TOKEN expires 2026-10-02 in 17 days.** Step 9J and the autonomous issue loop both die without it. GH #399 has been open 73 days with zero comments since the original filing. A new comment with "17 days to expiry" is materially different signal than an open issue with stale context.

### Verdict: **SURVIVES → WINNER**

Dedup handled. Urgency is time-bound (17 days). 2nd carry-forward per governance. GH comment creates email notification that static log line cannot. Highest risk/reward of all ideas.

---

## Idea 2: Fix Step 9G — mcp__github__actions_run_trigger instead of gh CLI

### Challenge

1. **MCP tool availability in nightly sessions unverified.** `mcp__github__actions_run_trigger` is listed as a deferred tool in this interactive session. Nightly sessions (CCR headless) may not have the same MCP config loaded. If the tool is unavailable in nightly, Step 9G silently breaks in a different way.

2. **Root cause not fixed.** Even if Step 9G successfully triggers kb-autopopulate.yml, the workflow fails because ANTHROPIC_API_KEY is missing in GH Actions (confirmed run 102). KB stays stale. The trigger just produces a failed run URL. Net improvement: a failure URL vs. "cannot trigger."

3. **kb-autopopulate.yml may not have workflow_dispatch trigger.** Run 115 mandate item 5 specified "verify kb-autopopulate.yml has workflow_dispatch trigger (Step 9G fix viability)" — this was never confirmed. If the workflow doesn't expose workflow_dispatch, mcp__github__actions_run_trigger will 422.

### Defend

1. **Better diagnostic is still progress.** Currently: "gh CLI not available" — human has no actionable next step. After fix: "Triggered kb-autopopulate.yml, Run URL: [URL], status: failed (ANTHROPIC_API_KEY missing)" — human can click the URL, see the specific failure, fix the secret. This IS an improvement even if KB stays stale.

2. **MCP availability likely but unverified.** The nightly sessions are CCR cloud sessions using the same project .mcp.json which includes the GitHub MCP. `mcp__github__actions_run_trigger` should be available. But the risk of a SKILL.md edit that silently breaks is real and unverifiable without a test run.

3. **workflow_dispatch trigger unverified.** This is a prerequisite that was flagged in run 115 and never confirmed. Without it, the fix fails on first nightly run.

### Verdict: **WEAKENED → PARKING LOT**

Correct direction but two unverified prerequisites: MCP tool in nightly session + workflow_dispatch trigger in kb-autopopulate.yml. Should be investigated and confirmed before implementing SKILL.md edit. Parking lot: confirm prerequisites in run 122 mandate, implement in run 122 or 123.

---

## Idea 3: Step 9L dedup fix — systemic label search before duplicate filing

### Challenge

1. **Is the dedup actually broken?** Step 9L already has dedup logic per the SKILL.md. The systemic issue GH #871 was filed today. Next nightly may successfully dedup if the implementation searches by title keyword or label.

2. **Filing 20 separate per-function issues is the correct outcome.** If Step 9L creates one issue per function, engineers can close individual issues as they fix them. A systemic summary issue doesn't give granular tracking.

3. **This is an optimization, not a bug.** No user-facing breakage. GH issue count is cosmetic. Spending a run recommendation on cosmetic cleanup is lower leverage than Idea 1 (credential expiry) or Idea 2 (KB self-healing).

### Defend

1. **Dedup is broken for systemic issues.** The SKILL.md says dedup searches for "existing open GH issue by filename." GH #871 is labeled billing+ai-ready but its title is "AI metering guards missing — 20 functions" not a filename. Per-filename search returns 0 results → next nightly files another systemic issue. 20+ violations × daily recurrence = rapidly accumulating duplicate GH issues.

2. **Systemic summary IS the right approach for 20+ violations.** Individual-per-function issues at 20+ functions creates 20+ individual items in the GH issue list simultaneously, overwhelming the human-action queue. One systemic summary issue with a comment per nightly is cleaner.

3. **Lower priority than Idea 1.** GH #871 was filed today — the harm accumulates slowly. Idea 1 is time-bound (17 days to credential expiry). Idea 3 should be run 122 candidate.

### Verdict: **WEAKENED → PARKING LOT (run 122 candidate)**

Real problem but not time-bound. Lower urgency than Idea 1. Defer to run 122.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 1: Step 9E credential GH issue filing | **SURVIVES → WINNER** | Implement recommendation, run 122 = autonomous |
| Idea 2: Step 9G MCP trigger fix | **WEAKENED** | Parking lot: verify prerequisites first |
| Idea 3: Step 9L dedup fix | **WEAKENED** | Parking lot: run 122 candidate |
| Idea 4: Step 9E auto-close | Not debated (lower priority than top 3) | Parking lot |
| Idea 5: Step 9E unknown-state GH issue | Not debated (subsumed by Idea 1) | Parking lot / part of Idea 1 implementation |
