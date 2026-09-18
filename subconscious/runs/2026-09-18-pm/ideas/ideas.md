# Improvement Ideas — Run 2026-09-18-pm (Run 123)

Generated: 2026-09-18-pm

---

### Idea 1: Step 9E 10-Day P0 Credential Expiry Escalation Tier
**Evidence:** AUTOPILOT_GH_TOKEN at 76d (threshold already crossed), expires 2026-10-02 (14 days away). P0 tier fires in ~4 days (day 80). 4th consecutive carry-forward (runs 119→120→121→122→123). Current Step 9E only comments on existing GH #399 — a thread with 7+ autonomous comments, 0 human responses — no escalated-severity P0 issue ever filed. When these tokens expire: nightly reviews stop, KB autopopulate stops, subconscious commits stop, issue-to-pr-loop stops.
**Action:** Edit Step 9E in `.claude/skills/nightly-commit-review/SKILL.md`. After existing >=76d logic, add branch: compute `days_remaining = next_due_date - today`; if `days_remaining <= 10`, search for existing open P0 credential issue (dedup guard); if none, file GH issue with labels `human-action-required + ops + P0`, title "P0: AUTOPILOT_GH_TOKEN expires in {N} days — rotate now or all automation stops".
**Impact:** Last-chance escalation before automation death. P0-labeled issue generates fresh email notification vs. noise in GH #399 thread.
**Category:** operational

---

### Idea 2: Governance Correction — Mark Step 9G Implemented
**Evidence:** Today's nightly confirms `step_9g: kb-autopopulate.yml queued via mcp__github__actions_run_trigger — SUCCESS`. Run 121 winner was the Step 9G MCP fix. Governance.json active_directions still has Step 9G with `status: pending`, `autonomous_executable_at_run: 124`. If uncorrected, run 124 may auto-propose Step 9G re-implementation.
**Action:** Update governance.json `active_directions` Step 9G entry: set `implemented: true`, `implemented_date: "2026-09-18"`, `verified_by: "nightly-2026-09-18 step_9g line"`.
**Impact:** Prevents governance false alarm at run 124; maintains accurate system state.
**Category:** workflow_efficiency

---

### Idea 3: os_tool_executions.py God Class GH Issue (Mandate Item)
**Evidence:** 783L file (CLAUDE.md Rule 9: >600L → factor out). 6th consecutive subconscious mention. No GH issue found per morning digest or mandate checks. Run 122 mandate explicitly: "file GH issue if not yet done (6th mention)". Class stable at 783L for 19+ days but growing risk as Agent OS sprint adds features.
**Action:** File GH issue: title "refactor(os_tool_executions.py): split 783L god class into focused modules". Labels: `tech-debt`, `ai-ready`, M-effort. Body: current L count, 3-4 natural split planes (action persistence, event dispatch, quota tracking, tool registry bridging).
**Impact:** Creates issue-to-pr-loop track; prevents further bloat; honors mandate.
**Category:** code_health

---

### Idea 4: Step 9J.2 — File GH Triage Issue for Major-Bump Dependabot PRs
**Evidence:** Today's nightly shows 5 Dependabot PRs (4 major bumps: React 18→19 across frontend + demo-platform, vitest 3→5; 1 CI unstable: mcp >=2.2). Step 9J correctly skips them (can't auto-merge). No tracking mechanism creates them as invisible aging debt.
**Action:** Add Step 9J.2 block: after skip loop, if `major_skip_count >= 2`, check for open GH issue listing these PRs; if none, file one with labels `dependencies + human-review-required`. List PR numbers and upgrade complexity. Cap: 1 issue per 7 days (dedup guard).
**Impact:** React 19 migration + vitest 5 tracked as single actionable item; no silent aging.
**Category:** operational

---

### Idea 5: Step 9N — AI Metering Violation Regression Detection
**Evidence:** Step 9L shows 45 violations (rc=2, unchanged). GH #827 open P1. Engineers fixing violations could introduce new ones in adjacent files during the sprint. No trend tracking; Step 9L only reports current snapshot.
**Action:** Add Step 9N: read Step 9L's violation count, compare to last stored count in `subconscious/state/step9l-history.json`, alert if count increased (regression) vs decreased (progress). Store count + date on each nightly run.
**Impact:** Detects regressions before they compound; confirms sprint is making progress each nightly.
**Category:** code_health
