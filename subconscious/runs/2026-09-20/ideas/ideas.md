# Ideas — Run 125 (2026-09-20)

## Idea 1: Step 9E 10-Day P0 Credential Expiry Escalation Tier (6th carry-forward)
**Evidence:** AUTOPILOT_GH_TOKEN: 78d elapsed, last rotated 2026-07-04, expires 2026-10-02 (12 days remaining). P0 threshold (≤10d) fires 2026-09-22 — **2 days from today**. nightly-commit-review-2026-09-20.md confirms warning. grep on `.claude/skills/nightly-commit-review/SKILL.md`: `days_remaining`=0 hits, `P0`=0 hits in Step 9E context — tier is ABSENT. GH #399 has 7+ comments with 0 human responses. If token expires: all cloud-container automation stops simultaneously (nightly review, subconscious push, issue-to-pr-loop, KB autopopulate). Autonomous-executable mandate passed at run 122. 6th consecutive carry (runs 119→125).
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block. After existing ≥76d staleness logic, add: compute `days_remaining = next_due_date - today`. If `days_remaining <= 10`: search open GH issues with labels [P0, ops] for credential name (dedup guard); if none found, file issue via `mcp__github__issue_write` with title "P0: {credential_name} expires in {days_remaining} days — rotate now", labels [human-action-required, ops, P0], body with expiry date + automation impact; if found, add comment with updated count. Update Step 9E log line to include K=P0 count.
**Impact:** P0 GH issue generates fresh email notification; surfaces in P0 issue views; categorically different urgency from staleness comment thread. Prevents all-automation blackout at 2026-10-02.
**Category:** operational

---

## Idea 2: Step 9G SKILL.md Fix — Replace gh CLI with mcp__github__actions_run_trigger (2nd carry-forward)
**Evidence:** Run 121 winner (2026-09-17). docs/dev-knowledge/nightly-reviews/2026-09-20.md Step 9G: "SKILL.md still uses broken gh workflow run bash command." grep on SKILL.md line 324 confirms `gh workflow run failed` — bash gh path still present, MCP fix NOT applied. KB autopopulate log shows last run 2026-08-26 (25 days stale — past 7-day threshold). KB staleness persists directly because Step 9G cannot successfully trigger the workflow.
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9G block. Replace `bash: gh workflow run kb-autopopulate.yml` invocation with `mcp__github__actions_run_trigger` tool call. The MCP path was confirmed working in run 121 evidence (available in tool list).
**Impact:** KB autopopulate trigger repair. KB freshness restored from 25-day staleness to <2-day lag. Downstream: wiki articles stay current, RAG quality improves for widget tenant queries.
**Category:** workflow_efficiency

---

## Idea 3: Step 9J Dependabot Major-Version Triage Issue
**Evidence:** nightly-reviews/2026-09-20.md: 5 Dependabot PRs open, 0 merged. All major version bumps: #864 (mcp major), #863 (react-dom 18→19 /demo), #861 (react 18→19 /demo), #860 (react 18→19 /frontend), #859 (vitest 4→5 /frontend). React 18→19 is a breaking-change migration requiring explicit effort budgeting. No consolidated triage tracking exists.
**Action:** File a GH issue consolidating all 5 PRs with migration effort estimate and priority order: vitest 4→5 first (lowest risk), react 18→19 second (medium, needs compatibility audit), mcp major third (unknown risk profile). Issue labels: [dependencies, tech-debt, human-action-required].
**Impact:** Single actionable entry point. Prevents PRs sitting open indefinitely; breaks "5 open, 0 merged" stall.
**Category:** code_health

---

## Idea 4: Step 9N — Metering Violation Trend Tracking
**Evidence:** Step 9L: 45 violations (unchanged across runs 123→124→125). GH #827 P1 open. But no trend data: are violations growing, stable, or shrinking? `backend/ai_usage_guard.py` enforcement is passive — reports but doesn't block. Without a trend counter, GH #827 risks stalling indefinitely with no urgency signal.
**Action:** Add Step 9N to nightly-commit-review SKILL.md. On each run, read the previous run's violation count from a state file (`ops/state/ai-usage-violations.json`) and compute delta. If delta > 0 (growing), add comment to GH #827 with trend. If delta = 0 for 7+ consecutive runs, escalate to P1 comment noting "stalled — requires human triage sprint." Write current count + date back to state file.
**Impact:** Converts passive tracking into active escalation. Triggers human attention when violations stall.
**Category:** operational

---

## Idea 5: os_tool_executions.py God-Class Split GH Issue (7th consecutive mention)
**Evidence:** `backend/services/os_tool_executions.py` is 783 lines (threshold: 600L). Run 123 memory: "bonus_actions: os_tool_executions.py GH issue filed (6th consecutive mention)" — a GH issue was reportedly filed at run 123. No commit evidence of splitting. 0 changes in 7d+. Stable, not actively breaking anything.
**Action:** Verify the GH issue from run 123 is still open. If open: no new action, add to parking lot as confirmed-tracked. If closed or missing: re-file with split plan (executor logic / OS commands / validation / registry pattern — 4 modules of ~200L each).
**Impact:** Code health improvement. Reduces blast radius for bugs in the service. Prerequisite for any refactor that touches the tooling layer.
**Category:** code_health
