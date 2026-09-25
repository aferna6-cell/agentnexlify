# Ideas — Run 130 (2026-09-25)

## Evidence Digest

- **Step 9J CONFIRMED IMPLEMENTED** by nightly-2026-09-25. Sort:created-asc + perPage=5 now in SKILL.md. Oldest Dependabot PRs processed first. Parking lot condition for Step 9G met.
- **KB stale 30 days** (last compiled 2026-08-26). Step 9G has been triggering kb-autopopulate.yml since run 101 (2026-08-06) but ANTHROPIC_API_KEY missing in GH Actions (GH #403) causes silent workflow failure. Step 9G logs "TRIGGERED — SUCCESS" after 30s passive wait regardless of actual outcome.
- **AUTOPILOT_GH_TOKEN expires 2026-10-02** (7 days). GH #399 still open. P0 tier in Step 9E fires correctly, but no auto-issue after ELAPSED state.
- **ops/routines/logs/nightly-commit-review-2026-09-25.md** confirms Step 9J fix applied, P0 alert carrying forward.
- **os_tool_executions.py** at 783L (CLAUDE.md Rule 9 threshold: 600L). 7th parking lot mention.
- **GH #827** open: 45 AI metering violations (billing + ai-ready labels).

---

### Idea 1: Step 9G KB Failure Diagnostics
**Evidence:** KB last compiled 2026-08-26 (30 days stale). Step 9G line ~336 of SKILL.md triggers kb-autopopulate.yml via mcp__github__actions_run_trigger then waits 30s and logs "TRIGGERED — SUCCESS" regardless of actual run outcome. GH #403 confirms ANTHROPIC_API_KEY missing from GH Actions. 15+ consecutive nightlies show false-positive success signal. Parking lot from run 129 explicitly names this as next candidate post-Step 9J clearance.
**Action:** In SKILL.md Step 9G, after 60s wait, poll kb-autopopulate.yml run status via mcp__github__actions_get (or equivalent list_actions → get_check_run lookup). If run status=failure: post targeted comment to GH #403 naming ANTHROPIC_API_KEY as likely culprit. Log "KB autopopulate: TRIGGERED+CONFIRMED" or "TRIGGERED — RUN FAILED (see GH #403)."
**Impact:** Ends 15+ consecutive false positive "success" log lines. Gives nightly log honest diagnostic. Accelerates KB recovery once human rotates secrets (GH #403). Converts silent failure to actionable notification.
**Category:** workflow_efficiency

---

### Idea 2: Step 9E ELAPSED Auto-Issue Filing
**Evidence:** AUTOPILOT_GH_TOKEN expires 2026-10-02 (7 days). Step 9E P0 tier fires correctly at days_remaining <= 10. But no mechanism auto-files a GH issue when credential actually hits ELAPSED state (days_remaining <= 0). Once elapsed, the nightly P0 log is there but no issue in GitHub creates an audit trail or prompts assignee workflow.
**Action:** In SKILL.md Step 9E, add ELAPSED branch: when days_remaining <= 0, call mcp__github__create_issue with title "ELAPSED: {credential_name} expired — automation broken", labels=[ops, P0, human-action-required]. Guard: file only once (check for existing ELAPSED issue before creating).
**Impact:** Creates persistent GH issue if token lapses. Human gets GitHub notification and issue URL in ops log. Nightly P0 logs stop being silent-dismissed; issue provides audit trail and assignee path.
**Category:** operational

---

### Idea 3: os_tool_executions.py God Class Split
**Evidence:** os_tool_executions.py confirmed at 783L (7th parking lot mention, CLAUDE.md Rule 9 threshold: 600L). god-class-splitter SKILL.md exists (created run 33, e848b87). Post-split-test-repair SKILL.md exists. 3 clean concerns identifiable: dispatch logic, execution tracking, result formatting.
**Action:** Invoke /god-class-splitter on os_tool_executions.py. Split into os_tool_dispatch.py + os_tool_execution_tracker.py + os_tool_result_formatter.py. Run post-split-test-repair after.
**Impact:** Brings 783L file under 600L threshold. Reduces blast radius of future OS tool additions. Unblocks CLAUDE.md Rule 9 compliance for this file.
**Category:** code_health

---

### Idea 4: GH #827 AI Metering Baseline Log
**Evidence:** GH #827 open with 45 billing + ai-ready labeled issues. Run 129 noted this as a mandate check item. No nightly log currently records a count of open ai-metering violations for trend detection. Count could be growing or shrinking — unknown.
**Action:** Add 3-line Step 9I/9H note to SKILL.md: count open issues with labels billing+ai-ready via mcp__github__search_issues, log "GH #827 ai-metering: {count} open". No action threshold — logging only for run 131+ trend comparison.
**Impact:** Provides baseline count for trend detection. Run 131+ can compare and escalate if count is rising. Closes run_130_mandate item 6 definitively.
**Category:** operational

---

### Idea 5: Step 9E Expiry State Persistence
**Evidence:** AUTOPILOT_GH_TOKEN P0 alerts have carried forward through runs 127–130 without rotation. Each nightly fires P0 log but no state file records "P0 already alerted — skip duplicate log". Redundant P0 logs across runs reduce signal clarity.
**Action:** After Step 9E fires P0, write ops/credential-state.json with {credential_name, last_alert_date, days_remaining_at_alert}. On subsequent runs, read state and suppress duplicate P0 log if alerted within 24h.
**Impact:** Reduces log noise. Preserves signal quality for genuine new P0 events. Makes ops log scannable across runs.
**Category:** operational
