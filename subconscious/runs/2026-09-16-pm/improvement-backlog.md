# Improvement Backlog — Run 121 (2026-09-16-pm)

---

## Active Directions (pending implementation)

### Step 9E — Credential Expiry GH Issue Filing
**Status:** 2nd carry-forward. AUTONOMOUS-EXECUTABLE at run 122.
**Urgency:** CRITICAL — AUTOPILOT_GH_TOKEN expires 2026-10-02 (16 days). Notification mechanism broken.
**What's needed:** Add `days_remaining <= 10` threshold to Step 9E in nightly-commit-review/SKILL.md. Search existing issues by label, comment on GH #399 or create new issue. PR #874 has the implementation sketch.
**Blocker:** Human has not undrafted/merged PR #874. Run 122 fires autonomous implementation if still unimplemented.

---

## Parking Lot (needs pre-verification before advancing)

### Step 9G — MCP Trigger Fix for KB Autopopulate
**Status:** 3rd appearance in parking lot. Still unverified.
**Problem:** gh CLI unavailable in cloud nightly sessions. Step 9G silently fails. KB 21 days stale. Brain connector 55 days stale.
**Proposed fix:** Replace `gh workflow run kb-autopopulate.yml` with `mcp__github__actions_run_trigger`.
**Pre-verification required before implementing:**
1. Confirm `mcp__github__actions_run_trigger` is available in nightly execution sessions (check deferred tool list)
2. Confirm `kb-autopopulate.yml` has `workflow_dispatch:` trigger defined
3. Confirm AUTOPILOT_GH_TOKEN has `workflow:write` scope for `actions_run_trigger`
4. Confirm that fixing the trigger actually helps — or is it blocked by GH #403 (missing ANTHROPIC_API_KEY in GH Actions secrets)?
**Deeper blocker:** GH #403 is human-action-required. Step 9G working correctly would trigger a workflow that fails due to missing ANTHROPIC_API_KEY. Fix Step 9G only after confirming the Actions workflow itself works.
**Escalation:** Run 122 should do the pre-verification checklist. If all 4 checks pass → ready to implement at run 123.

---

## Active External Issues (not subconscious-owned, monitoring)

### GH #875 — 40 AI Metering Violations
**Status:** Filed 2026-09-16 by nightly review. Labels: ai-ready, nightly-review, billing.
**Owner:** issue-to-pr-loop (polls ai-ready issues every 15 min).
**Subconscious role:** Monitor. If not picked up by issue-to-pr-loop within 24h, flag in run 122 mandate.
**Context:** 40 production call sites call Claude API without `ai_usage_guard` check. Free-plan tenants can burn unbounded tokens. GH #871 previously filed for this; #875 is the updated count (44→40 after 4 fixes landed).

### GH #403 — ANTHROPIC_API_KEY Missing from GH Actions
**Status:** Long-standing human-action-required. Blocks KB autopopulate + autopilot loop.
**Owner:** Human (GitHub UI → Settings → Secrets).
**Subconscious role:** Track only. Cannot be resolved by automation.

### GH #800 — Brain Connector Dead (55 days)
**Status:** Long-standing human-action-required. Last run 2026-07-23.
**Owner:** Human (reconnect brain connector).
**Subconscious role:** Track only.

### GH #399 — AUTOPILOT_GH_TOKEN Rotation Tracking
**Status:** Open. Should receive automated Step 9E comments once Step 9E is implemented.
**Owner:** Human (rotate token). Subconscious (file issue comments after Step 9E implemented).
**Deadline:** Rotate before 2026-10-02.

---

## Rejected / Frozen Ideas

### Widget Drift Topic
**Status:** Retired (governance flag `widget_drift_topic_retired: true`). Widget byte-identical enforcement already handles this via CI invariant.

### AI Human Handoff
**Status:** Frozen (governance flag). Too architectural for autonomous recommendation.

### os_tool_executions.py God Class Split
**Status:** Repeatedly deferred. Currently deferred again — file modified 2026-09-11, stability window broken.
**Re-evaluate:** After 14+ days of no modification (earliest: ~2026-09-25).

### React 19 Upgrade Gate in Step 9J
**Status:** Low priority. Morning digest already surfaces this. Subconscious amplifying would be redundant.
**Owner:** Human (run `cd frontend && npm run build` against each PR before merging).

---

## Open Questions for Next Run

1. **Step 9E autonomous implementation**: If still unimplemented at run 122, autonomous mode fires. What's the exact SKILL.md diff to apply? (Answer: see winning-concept.md Implementation section — the code block is the diff.)
2. **Step 9G pre-verification**: Can `mcp__github__actions_run_trigger` be called in a nightly session? Check `ToolSearch` for the tool schema in next nightly.
3. **SUPABASE_ACCESS_TOKEN**: Human needs to fill in `last_rotated` date in `ops/credential-rotation-schedule.md`. Is there even a rotation schedule file at that path?
4. **GH #875 pickup**: Has issue-to-pr-loop claimed #875 within 24h of filing? Check next run.
5. **Check 10 planner invariant**: Pre-commit check fails "planner tool_catalog matches Action manifest" due to missing pydantic module. Is this blocking any commits or is it warning-only?
