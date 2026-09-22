# Run 126 — Candidate Ideas

Generated: 2026-09-22 (pm run)
Evidence window: 2026-09-21 to 2026-09-22

---

## Idea 1: Step 9G SKILL.md Fix — Replace `gh` CLI with `mcp__github__actions_run_trigger`
**Category:** Workflow Efficiency
**Evidence:**
- Step 9G in nightly-commit-review SKILL.md uses `gh workflow run kb-autopopulate.yml` bash command
- `gh` CLI is unavailable in CCR (Cloud Code Runtime) — confirmed fail in multiple prior runs
- KB is 27 days stale (last run 2026-08-26), directly caused by this broken trigger
- mcp__github__actions_run_trigger confirmed working in-session workaround (run 122, 2026-09-18)
- GH #893 P0 credential rotation is imminent — once rotated, KB recovery depends on Step 9G firing correctly
- 3rd carry-forward; autonomous-executable since run 124

**Proposed fix:** Replace bash `gh workflow run kb-autopopulate.yml` with `mcp__github__actions_run_trigger` MCP call in SKILL.md Step 9G block. Single targeted edit, no logic change.

**Carry-forward count:** 3 (autonomous-executable)
**Effort:** S (1 SKILL.md section edit)
**Impact:** H (unblocks KB autopopulate pipeline that's been broken for 63+ days)

---

## Idea 2: Step 9E P0 Credential Expiry Tier (7th carry)
**Category:** Operational
**Evidence:**
- AUTOPILOT_GH_TOKEN expires 2026-10-02, 10 days away
- Brain PAT same expiry
- GH #893 filed today as emergency P0 notification
- Step 9E nightly SKILL.md still has NO `days_remaining <= 10` escalation path
- Without P0 tier: expiry fires silently, automation stops at midnight 2026-10-02
- 6 consecutive carries (runs 119–125); autonomous-executable since run 122

**Proposed fix:** Add P0 tier block to Step 9E in SKILL.md that:
  - Detects `days_remaining <= 10`
  - Fires PushNotification immediately (not just morning digest mention)
  - Files GH issue with `human-action-required` + `P0` labels

**Carry-forward count:** 6 (task-prompt deadlock — "recommend only" overrides autonomous-execute)
**Effort:** S
**Impact:** H (but GH #893 provides immediate path independently)

**Status note:** Demoting to parking lot this run. GH #893 filed as manual mitigation. Deadlock between autonomous-executable mandate and task-prompt constraint after 6 carries warrants winner rotation.

---

## Idea 3: GH #892 CI Safety Test Escape — Diagnose Root Cause
**Category:** Code Health
**Evidence:**
- GH #892 opened 1d ago: "staging credential rejection test escapes to network"
- Labeled `bug, p1, ci, blocker`
- Any deploy while this is unfixed risks staging credentials leaking to real network
- Morning digest flags as Priority 2
- No commits addressing it in 48h window

**Proposed fix:** Read test file, identify mock boundary failure, add `unittest.mock.patch` or equivalent to contain network escape. File patch PR.

**Carry-forward count:** 0 (new evidence today)
**Effort:** M (read failing test + root-cause)
**Impact:** H (P1 blocker, deploy risk)

---

## Idea 4: Dependabot PR Merge Throughput — Audit Step 9J Token Budget
**Category:** Workflow Efficiency
**Evidence:**
- 6 new Dependabot PRs today (#885–#891): bcrypt, supabase, uvicorn, google-api-python-client, vitest, jsdom
- Step 9J processes Dependabot PRs but has systematic skip rate: 17/19 PRs skipped per run per prior analysis
- Morning digest: "Review and merge dependabot PRs — all safe maintenance bumps"
- PRs accumulate: 6 new + likely backlog = queue pressure

**Proposed fix:** Audit Step 9J token budget and processing logic. Check if skip threshold is too conservative. Consider increasing `max_prs_per_run` or adjusting risk scoring.

**Carry-forward count:** 0
**Effort:** S-M
**Impact:** M (quality-of-life; queue pressure manageable manually)

---

## Idea 5: os_tool_executions.py God-Class Split — File GH Issue Spec
**Category:** Code Health / Tech Debt
**Evidence:**
- `backend/os_tool_executions.py` = 783 lines, god-class candidate
- GH #881 open (`tech-debt, ai-ready`) for refactor
- 6th consecutive mention in subconscious evidence
- User rule 9: "If a file is already >600 lines and I'm about to add more, stop. Factor the existing code into modules first."
- No commits touching it in 48h window; #881 not assigned

**Proposed fix:** Write detailed spec comment on GH #881 with proposed split: identify top-level concern boundaries, suggest module names, estimate migration order.

**Carry-forward count:** 3+ (recurring evidence, no action)
**Effort:** S (spec only — no code change)
**Impact:** M (sets up future ai-ready work; unblocks #881 assignment)
