# Candidate Ideas — Run 2026-09-16 (Run 121)

---

### Idea 1: Step 9E — Extend credential expiry alert to fire at days_remaining ≤ 10 and file GH issue (2nd carry-forward)

**Evidence:**
- AUTOPILOT_GH_TOKEN: 74 days old as of 2026-09-16 (threshold 76d, expires 2026-10-02 = 16 days away)
- nightly-2026-09-15 Step 9E output: "2 credentials checked, 0 approaching expiry" — fired at 73d < 76d threshold, so no alert issued
- Step 9E SKILL.md line 287: `days_since_rotation >= 76` — fires at 76d only (too late for advance notice)
- No GH issue filed; no comment on GH #399 — human has not been notified despite token expiring in 16 days
- Run 120 winning-concept.md: implementation sketch ready (search by label "credential-rotation", comment on GH #399 if found, create new issue if not)
- run_120.carry_forward_count = 1 → today is 2nd carry-forward

**Action:**
Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block:
- Change threshold from `days_since_rotation >= 76` to `days_remaining <= 10` where `days_remaining = 90 - days_since_rotation`
- Add GH issue search by label `credential-rotation` + credential name
- Comment on existing issue (GH #399 for AUTOPILOT_GH_TOKEN) or create new issue
- Log: "Step 9E: {N} credentials checked, {M} approaching expiry, {K} issues filed/commented"

**Impact:**
- Prevents silent loop death from AUTOPILOT_GH_TOKEN expiry (2026-10-02)
- Fires 14+ days before threshold (not day-of)
- Human gets GH email notification via issue comment vs. silent log line
- Autonomous-executable at run 122 (3rd carry-forward) if not approved by today

**Category:** workflow_efficiency

---

### Idea 2: Step 9G MCP trigger fix — replace unavailable gh CLI with mcp__github__actions_run_trigger

**Evidence:**
- nightly-2026-09-15 Step 9G: "gh CLI not available in this environment. Cannot trigger workflow run."
- nightly-2026-09-16 Notes: "KB 21d stale (#403)" — Step 9G is broken so KB self-heal never fires
- KB stale since 2026-08-26 (21 days, threshold 7 days) — AI chat answers are 3 weeks stale
- mcp__github__actions_run_trigger IS available in headless sessions (confirmed: other subconscious runs use GitHub MCP tools)
- kb-autopopulate.yml has `workflow_dispatch` trigger (run 99 governance confirms)
- Step 9G was implemented in run 101; gh CLI workaround was noted as broken in run 116 but fix deferred

**Action:**
Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9G block:
- Replace `bash: gh workflow run kb-autopopulate.yml` with `mcp__github__actions_run_trigger(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml", ref="main")`
- Remove `gh CLI not available` fallback path
- Keep 30s wait + status check via `mcp__github__actions_list`

**Impact:**
- KB self-heal resumes functioning: 21-day stale → auto-triggered within 24h
- AI chat answers stop being 3 weeks stale
- Fixes a Step 9G that has been broken for 10+ runs without anyone noticing

**Category:** operational

---

### Idea 3: GH #870 batch remediation script — generate per-file block_demo_role patch checklist

**Evidence:**
- nightly-2026-09-15 Step 9I: "90+ backend/routers/ files with mutating endpoints missing Depends(block_demo_role)" → GH #870 filed
- GH #870 is a summary issue; no per-file action items generated
- Pattern from Step 9I: it detects but doesn't generate remediation artifacts
- GH #870 will sit unacted-upon like GH #413 unless it's broken into actionable pieces
- Previous individual block_demo_role issues (GH #643, #661) took 7-10 days each; 90+ issues would take years at that pace
- `scripts/check_ai_metering.py` precedent (run 117): AST-based detector + per-violation issue filing worked for AI metering

**Action:**
Create `scripts/generate_demo_role_patch.py` — reads Step 9I violation output, groups by router file, generates skeleton patch commands (one `Depends(block_demo_role)` insertion per mutating route). Output: list of file+line+current_signature → patched_signature. File GH #870 comment with first 20 as actionable checklist.

**Impact:**
- Converts 90+ vague "missing guard" findings into 90 specific 1-line patches
- Reduces human decision cost from "fix 90 files" to "approve 90 diffs"
- Prevents GH #870 from aging like #413 (5+ months, 0 action)

**Category:** code_health

---

### Idea 4: AI metering middleware proposal — class-level fix for GH #875's 40 violations

**Evidence:**
- nightly-2026-09-15 Step 9L: 20 violations → GH #871; nightly-2026-09-16: 40 violations → GH #875, closed #871
- Pattern: per-function fixes create one PR per function (previous metering sprint: PRs #792-#799 = 8 PRs for 6 functions)
- 40 violations × 1-2 PRs each = 40-80 future PRs needed
- FastAPI middleware pattern: a single `ai_metering_middleware.py` could intercept all `/api/` calls and apply usage guard at request-scope rather than per-endpoint
- All AI endpoints already flow through the same `call_claude_messages` bottleneck in `llm_runtime.py`
- Architectural fix eliminates the category, not just instances

**Action:**
File GH issue proposing `backend/middleware/ai_metering_middleware.py` that wraps `call_claude_messages` to automatically apply `reserve_tokens` / `record_tokens` for any request that triggers an AI call — backed by the request's authenticated `client_id` from the JWT context. This eliminates per-function boilerplate and prevents regression.

**Impact:**
- 40 violations resolved in 1 PR instead of 40-80 PRs
- Prevents future metering regressions (enforcement is structural, not per-author)
- Closes Step 9L permanently once middleware is in place

**Category:** code_health

---

### Idea 5: Brain connector staleness — add automated GH #800 comment when stale exceeds 30 days

**Evidence:**
- Brain connector: 55 days stale (last run 2026-07-23) — per nightly-2026-09-15 Step 9C
- Step 9C fires age-gate warning at 14 days (implemented run 103) and comments on GH #800
- GH #800 comment has been added multiple times (runs 103-120) but human has not acted
- After 30+ days stale, the brain connector's data is so stale that it's generating incorrect context for the AI system
- No escalation mechanic: Step 9C comments are low-priority notes; at 55 days the issue is critical
- Pattern precedent: runs 90-92 added Day-21/Day-22 escalation comments on booking issues that successfully prompted human attention

**Action:**
Extend Step 9C in SKILL.md: add a second threshold at 30+ days stale. When `days_stale >= 30`, post an escalation comment on GH #800 with priority label P0 + `human-action-required`. Dedup: only comment if no escalation comment in last 7 days.

**Impact:**
- Escalates brain connector from "heads-up" to "urgent: action required" tier
- Distinguishes 14-day warning from 30-day critical failure
- Prompts human action on a 55-day stale system that's actively degrading AI context quality

**Category:** operational
