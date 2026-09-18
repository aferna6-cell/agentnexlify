# Ideas — Run 2026-09-18 (Run 122)

## Evidence Base
- Nightly review 2026-09-18: 4 commits (all ops/docs/subconscious — no production code)
- Step 9E: AUTOPILOT_GH_TOKEN + Brain PAT at **76 days** (threshold crossed today), expires 2026-10-02 (14 days). Comment added to GH #399.
- Step 9G: SKILL.md still has broken `gh workflow run` bash command. In-session MCP workaround applied. 1st carry-forward from run 121.
- Step 9J: 5 Dependabot PRs, 0 merged (4 major version bumps, 1 CI unstable)
- Step 9L: 45 violations (unchanged), "owner tracking separately" — no confirmed canonical GH issue
- os_tool_executions.py: 783 lines, stable 19d+, 5th consecutive subconscious mention
- Governance chain: Step 9E 10-day early warning at 3rd carry-forward → **AUTONOMOUS-EXECUTABLE** this run (runs 119→120→121→122)

---

## Idea 1 — Step 9E: Add 10-Day P0 Escalation Tier (WINNER)
**Category:** operational / workflow_efficiency
**Effort:** S (single block edit in SKILL.md Step 9E)
**Confidence:** HIGH
**Carry-forward count:** 3 (autonomous-executable)

**Problem:** Step 9E's >=76d threshold fires warnings but has no escalation when expiry is imminent (≤10 days). With AUTOPILOT_GH_TOKEN expiring 2026-10-02 (14 days), the 10-day tier will fire in ~4 days. If it's not implemented, the loop dies silently when the token expires — no automation runs, no commits, no self-improvement loop.

**Proposed fix:** Add `days_remaining <= 10` detection in Step 9E block. When any tracked credential hits this tier:
1. Compute `expiry_date - today` in days
2. If `days_remaining <= 10`: file P0 GH issue with labels `human-action-required`, `ops`, `P0` — title: "P0: [CREDENTIAL] expires in N days — rotate NOW"
3. Dedup guard: search existing open issues for credential name + "expires" before filing
4. Add comment to GH #399 noting P0 escalation fired

**Why autonomous-executable:** 3rd consecutive carry-forward per governance chain. Runs 119 (identified), 120 (1st carry-forward), 121 (2nd carry-forward), 122 = MUST implement. Governance mandates execution, not recommendation.

---

## Idea 2 — Fix Step 9G SKILL.md: Replace `gh workflow run` with MCP
**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit)
**Confidence:** HIGH
**Carry-forward count:** 1 (autonomous-executable at run 124)

**Problem:** Step 9G bash command uses `gh workflow run kb-autopopulate.yml` which fails silently in CCR. Run 121 winner. Nightly has been applying in-session workaround but SKILL.md is still broken.

**Proposed fix:** Replace bash block with pseudocode directing use of `mcp__github__actions_run_trigger` and handle success/failure with diagnostic comment on GH #403.

**Status:** Run 121 winner, 1st carry-forward. Autonomous-executable at run 124 (2 more carry-forwards needed).

---

## Idea 3 — File P0 GH Issue: Rotate AUTOPILOT_GH_TOKEN + Brain PAT Before 2026-10-02
**Category:** operational / human-escalation
**Effort:** XS (single GH issue creation)
**Confidence:** HIGH
**Carry-forward count:** 0 (new)

**Problem:** AUTOPILOT_GH_TOKEN and Brain connector PAT expire 2026-10-02 (14 days). Step 9E added a comment to GH #399 (existing credential rotation tracking issue) but has not filed a P0-labeled issue to surface urgency. Without rotation, all CCR-based automation stops.

**Note:** Idea 1 (if implemented) will handle this systemically via the ≤10d tier in ~4 days. Filing this issue now provides immediate escalation before the 10-day tier kicks in.

---

## Idea 4 — File GH Issue: os_tool_executions.py 783L God Class Split
**Category:** code_quality / architecture
**Effort:** XS (GH issue creation only — no code)
**Confidence:** MEDIUM
**Carry-forward count:** 5th consecutive mention

**Problem:** `backend/services/os_tool_executions.py` is 783 lines, stable 19d+, mentioned in 5 consecutive subconscious runs. Rule 9 threshold (600L) exceeded. No GH issue filed yet to track the split. The file is stable, which means now is a safe time to plan the refactor without conflict risk.

**Proposed fix:** File GH issue with label `code-quality` documenting the god class, Rule 9 reference, and proposed split into service modules (executor, parser, validator, etc.). Human reviews and assigns.

---

## Idea 5 — Verify/File Canonical AI Metering Tracking Issue (Step 9L)
**Category:** operational / visibility
**Effort:** XS (investigate + optionally file)
**Confidence:** LOW
**Carry-forward count:** 0 (new observation)

**Problem:** Step 9L reports 45 violations with "owner tracking separately" but no confirmed canonical GH issue number. If no issue exists, owner has no tracked action item. If multiple issues exist, tracking is fragmented.

**Proposed fix:** Search GH issues for "AI metering" or "ai_usage_guard" to find the canonical tracking issue. If absent, file one. If present, verify it's labeled and assigned.

**Note:** Low confidence because we don't know whether the issue already exists (Step 9L's comment was vague). Insufficient evidence to prioritize over the governance mandate.
