# Ideas — Run 2026-09-19 (Run 124)

## Evidence summary
- Git log (3d): 4 commits, all subconscious/ops/docs state. No production code changes.
- Nightly review 2026-09-19: AUTOPILOT_GH_TOKEN 77d elapsed, expires 2026-10-02 (**13 days remaining**). P0 fires 2026-09-22.
- Step 9E grep: `days_remaining` = 0 hits, `P0` = 0 hits in SKILL.md — P0 tier ABSENT.
- Step 9G: SKILL.md bash command still uses `gh` CLI (unavailable in CCR). In-session workaround applied 2026-09-18 only.
- Step 9J: 5 Dependabot PRs open (all major-version bumps), 0 merged.
- Step 9L: 45 AI usage violations (rc=2), GH #827 tracking.
- os_tool_executions.py: 783L god class, 6th+ consecutive subconscious mention.

---

## Idea 1 — Step 9E: Add 10-Day P0 Credential Expiry Escalation Tier [CARRY-FORWARD #5]
**Category:** operational / workflow_efficiency
**Effort:** S
**Evidence:** AUTOPILOT_GH_TOKEN expires 2026-10-02 (13d). P0 threshold (≤10d) fires 2026-09-22 — 3 days. grep confirms P0 tier absent from SKILL.md. GH #399 has 7+ comments, 0 human responses. A fresh P0 issue with `human-action-required` label generates a new email notification. 5 consecutive runs (119→124) with identical evidence.
**Risk:** LOW — additive SKILL.md edit, no production code.

---

## Idea 2 — Step 9G: Replace Broken `gh` CLI Command in SKILL.md with `mcp__github__actions_run_trigger`
**Category:** workflow_efficiency
**Effort:** S
**Evidence:** Step 9G bash block uses `gh workflow run kb-autopopulate.yml` — `gh` CLI is unavailable in CCR sessions. In-session MCP workaround confirmed working 2026-09-18 (status 204). KB is 24d stale. Every nightly run after SKILL.md fix attempt that used the bash path would fail silently. Run 121 winner was this exact fix; autonomous-executable at run 124.
**Risk:** LOW — replaces broken command with working equivalent.

---

## Idea 3 — Dependabot Major-Version PR Triage — File Coordinated Upgrade GH Issue
**Category:** code_health / operational
**Effort:** M
**Evidence:** 5 Dependabot PRs open (react 18→19 ×3, vitest 4→5, mcp >=2.2.0,<3). All skipped as "major version — human review required." No coordinated upgrade plan or tracking issue exists. These will keep accumulating. react 18→19 is a known breaking-change migration requiring codemods. Vitest 4→5 similarly. Without a tracking issue, each nightly review re-records the same skip.
**Risk:** LOW (filing issue only) — upgrade execution is human-gated.

---

## Idea 4 — Step 9M: Add AI Metering Trend Tracking to Nightly Review
**Category:** operational / monitoring
**Effort:** M
**Evidence:** Step 9L reports 45 violations (rc=2, GH #827). Current Step 9L only counts violations — it doesn't track trend (increasing/stable/decreasing). Without trend data, the owner can't tell if #827 actions are reducing violations. Needs 7-day rolling count and delta vs previous run to signal progress.
**Risk:** LOW — new monitoring step, no production changes.

---

## Idea 5 — Factor os_tool_executions.py God Class (783L → Focused Modules)
**Category:** code_health / tech_debt
**Effort:** L
**Evidence:** os_tool_executions.py at 783L, 6th+ consecutive subconscious mention. GH issue may have been filed in run 123 bonus action (mandate item). No GH issue confirmed open yet. Rule 9 in user-rules.md: files >600L → factor before adding. Natural split planes: action persistence, event dispatch, quota tracking, tool registry bridge.
**Risk:** MEDIUM — requires cross-file refactor.

---

## Top 3 for debate
1. Step 9E P0 tier (CRITICAL — P0 fires in 3 days, token expiry in 13 days)
2. Step 9G SKILL.md fix (HIGH — broken nightly action, but in-session workaround exists)
3. Dependabot triage issue (MEDIUM — accumulating skip entries, easy to unblock)
