# Ideas — Run 127 (2026-09-23)

## Evidence Digest

Today's nightly (2026-09-23) confirmed Step 9G IMPLEMENTED — `mcp__github__actions_run_trigger`
now replaces broken `gh CLI` in nightly-commit-review SKILL.md (run 126 winner, 3rd carry, done by
nightly-2026-09-23 LOW-risk auto-fix). Repo quiet 4+ days: zero production code commits.
AUTOPILOT_GH_TOKEN expires 2026-10-02 (9 days). GH #893 P0 filed but no human response.
KB 27+ days stale. Step 9E (P0 credential expiry tier) absent from SKILL.md — 6-carry parking lot
item unblocked now that Step 9G is done.

---

### Idea 1: Step 9E — Add 10-Day P0 Credential Expiry Escalation Tier
**Evidence:** Step 9E absent from SKILL.md (grep: days_remaining=0 hits, P0 in Step-9E context=0 hits).
AUTOPILOT_GH_TOKEN expires 2026-10-02 — 9 days from now, P0 threshold already crossed.
GH #893 filed but provides one-time manual notification only. Step 9G implemented today (run 126 winner,
3rd carry) — KB recovery pipeline now working. Step 9E was parked in run 126 due to task-prompt
constraint; autonomous-executable mandate binding since run 122. Same SKILL.md channel as Steps
9F/9G/9I/9J/9K (all successfully implemented).
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block — add computation of
`days_remaining` for each credential (interval - days_since_last_rotated), add <= 10 day P0 escalation
tier: file GH issue (labels: P0, ops, human-action-required) if no existing open P0 issue for that credential.
**Impact:** Prevents silent automation blackout from future token expiry. P0 tier fires in tomorrow's
nightly for AUTOPILOT_GH_TOKEN (9 days → P0). Compounds permanently.
**Category:** operational/workflow_efficiency

---

### Idea 2: File GH Issue for os_tool_executions.py God-Class Split
**Evidence:** os_tool_executions.py at 783L, mentioned 6+ consecutive runs (115→127) as god-class
split candidate. Governance mandated GH issue filing in run 122/123 bonus actions. Direct check
2026-09-23: file not yet found in git log as having a GH issue number. Rule 9 (god classes > 600L →
factor out first). Agent OS is actively shipping new tool executions — blast radius grows each sprint.
**Action:** File GH issue: "refactor(agent_os): split os_tool_executions.py (783L) into
os_tool_dispatch.py + os_tool_state.py + os_tool_executor.py". Labels: refactor + agent-os + ai-ready.
Body: concern mapping, estimated 3 new files, acceptance criteria.
**Impact:** Unblocks autopilot-issue-loop when GH #399 resolves. Prevents further god-class growth.
**Category:** code_health

---

### Idea 3: Step 9M — AI Metering Violation Trend Tracking in Nightly
**Evidence:** Step 9L deployed. GH #827 (P1) open with 45 unguarded AI-calling functions. Nightly
Step 9L fires but doesn't report trend (count change vs. last run). Without trending, violations could
silently increase as new features land — a spike is invisible until it's large. PRs #792-#799 each
added 498-1726 test lines to fix single metering gaps — retroactive cost is high.
**Action:** Add Step 9M block to SKILL.md after Step 9L: read last Step 9L count from nightly log,
compute delta vs current scan, log trend. If delta > 0 (violations increased): escalate comment on
GH #827. Summary: "Step 9M: {N} violations this run, {D:+/-} vs last run."
**Impact:** Catches metering regressions within 24h. Prevents multi-week retroactive metering sprints.
**Category:** code_health/workflow_efficiency

---

### Idea 4: Fix GH #892 — CI Safety Tests Escaping to Network
**Evidence:** nightly-2026-09-23 lists GH #892 (P1) as "CI safety test escaping to network". Test
isolation failure allows CI tests to make real network calls. This causes false positives, test
non-determinism, and security risk (test data hitting live services). Filed 2026-09-22.
**Action:** Diagnose which test file/class is making network calls in CI. Add `@pytest.mark.no_network`
marker or mock the escaping calls. Add CI conftest enforcement to block unmarked outbound calls.
**Impact:** Eliminates P1 CI reliability risk. Prevents flaky CI green→red cycles.
**Category:** code_health

---

### Idea 5: Step 9N — Credential Rotation Reminder Comment Automation
**Evidence:** ops/credential-rotation-schedule.md exists (run 104 winner) but `last_rotated` fields
are blank (`unknown`) for multiple credentials including SUPABASE_ACCESS_TOKEN. Step 9E tracks
approach-to-expiry but can't fire without valid `last_rotated` dates. Blanks cause silent Step 9E
skips (no days_remaining computable). Human never filled in last_rotated dates despite run 104 mandate.
**Action:** Add Step 9N block to SKILL.md: for each credential with last_rotated=unknown or > 90 days,
post a reminder comment on GH #800 (SUPABASE_ACCESS_TOKEN) or equivalent tracking issue with exact
Supabase/Railway dashboard path to find the rotation date. One comment per credential per week (dedup guard).
**Impact:** Enables Step 9E to compute days_remaining for all credentials. Closes silent-skip gap.
**Category:** operational/workflow_efficiency
