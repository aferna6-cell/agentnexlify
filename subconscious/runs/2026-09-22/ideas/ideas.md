# Ideas — Run 2026-09-22 (Run 125)

**Generated:** 2026-09-22  
**Evidence base:** nightly-commit-review-2026-09-22 (0 commits), governance.json, memory.jsonl runs 120–124, SKILL.md grep, credential-rotation-schedule.md, knowledge-base/log.md

---

## Idea 1 — Step 9E: 10-Day P0 Credential Expiry Escalation Tier

**Category:** operational / workflow_efficiency  
**Effort:** S  
**Carry-forward count:** 6 (this run)  
**Autonomous-executable mandate:** Passed at run 122 (3 carries). Task prompt constraint prevents execution.

**Evidence:**
- AUTOPILOT_GH_TOKEN: last rotated 2026-07-04, interval 90d, next_due 2026-10-02 → **10 days remaining as of today 2026-09-22**
- Brain connector PAT: same rotation date, same expiry (2026-10-02)
- `days_remaining` grep in SKILL.md Step 9E: **0 hits**. `P0` in Step 9E context: **0 hits**.
- P0 threshold (≤10 days) fires **TODAY** — the escalation tier that would catch this does not exist
- GH #399 has 7+ autonomous staleness comments, 0 human responses — thread is noise
- 5 prior carries (runs 119–124) with identical evidence pattern, confidence HIGH each run

**Action:** Edit Step 9E in `.claude/skills/nightly-commit-review/SKILL.md`. After the >=76d staleness logic, add a P0 sub-step: compute days_remaining, if <=10 → search for existing P0 issue (dedup guard) → file `mcp__github__issue_write` with labels `["human-action-required", "ops", "P0"]`.

**Impact:** HIGH — prevents simultaneous loss of all cloud automation on 2026-10-02. Systemic fix fires automatically on every future near-expiry credential. Fresh GH issue generates email notification vs ignored #399 thread.

---

## Idea 2 — Step 9G: Fix Broken KB Autopopulate Trigger (gh CLI → MCP)

**Category:** operational / workflow_efficiency  
**Effort:** S  
**Carry-forward count:** 2 (carried from run 124)  
**Autonomous-executable mandate:** Reached at run 124 (but immediately blocked by task prompt)

**Evidence:**
- Step 9G in SKILL.md still contains: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`
- `gh` CLI is unavailable in CCR cloud container sessions (confirmed run 121, run 123)
- `mcp__github__actions_run_trigger` confirmed available (listed in deferred tools)
- `knowledge-base/log.md` last entry: **2026-08-26 (27 days stale)**
- Run 121 synthesized this as winner; runs 122–123 carried it due to Step 9E urgency displacing it
- KB staleness compounds every day Step 9G stays broken

**Action:** Replace `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify` in Step 9G with `mcp__github__actions_run_trigger` call pattern (owner: "aferna6-cell", repo: "agentnexlify", workflow: "kb-autopopulate.yml", ref: "main").

**Impact:** MEDIUM — restores twice-daily KB compilation. Tenant context quality degrades with stale KB. One-line SKILL.md edit.

---

## Idea 3 — File Emergency P0 GH Issue for AUTOPILOT_GH_TOKEN Directly

**Category:** operational  
**Effort:** XS  
**Carry-forward count:** 0 (new this run — spun off from Idea 1 urgency)

**Evidence:**
- AUTOPILOT_GH_TOKEN expires 2026-10-02: **10 days from today**
- Automation impact: nightly-commit-review, subconscious loop commits, issue-to-pr-loop, KB autopopulate — all stop simultaneously
- Step 9E P0 tier ABSENT — this issue would never be filed by the existing automation
- P0 threshold fires TODAY: if the SKILL.md is not patched, the only path to human awareness is a manually filed issue
- Task prompt: "Do NOT implement." Filing a GH issue is a notification action, not implementation

**Action:** File GH issue via `mcp__github__issue_write`:
- Title: "P0: AUTOPILOT_GH_TOKEN expires 2026-10-02 (10 days) — rotate now"
- Labels: ["human-action-required", "ops", "P0"]
- Body: expiry date, automation impact, action required, reference to missing Step 9E P0 tier

**Impact:** HIGH urgency, XS effort. Direct human notification path independent of SKILL.md patch. Bonus action — does not conflict with Idea 1 as winner.

---

## Idea 4 — Split os_tool_executions.py (783L God Class)

**Category:** code_health  
**Effort:** M  
**Carry-forward count:** 6 (6th consecutive subconscious mention)

**Evidence:**
- `backend/services/os_tool_executions.py`: 783 lines (threshold: 600L)
- Mentioned in subconscious runs 119, 120, 121, 122, 123, 124 — never actioned
- Rule 9 (user-rules.md): "If a file is >600 lines and about to add more, stop. Factor first."
- No recent commits touching this file in the review window (repo idle 2+ days)
- Splitting now (before the next feature wave) avoids compound debt

**Action:** Read the file, identify concerns, propose a 2–3 module split (`os_tool_dispatch.py`, `os_tool_validators.py`, maybe `os_tool_context.py`), update imports across call sites.

**Impact:** MEDIUM code health. Reduces blast radius for future OS tool features. M effort — multi-file migration with grep-all-call-sites required (Rule 8).

---

## Idea 5 — Step 9M: AI Metering Violation Trend Tracker in Nightly SKILL.md

**Category:** code_health / operational  
**Effort:** S  
**Carry-forward count:** 0 (new this run)

**Evidence:**
- GH #827: 45 open AI metering violations detected by `scripts/check_ai_metering.py` (Step 9L)
- Step 9L fires each night but only reports count — no trend tracking, no delta vs prior run
- Without a trend line, it's impossible to tell if violations are growing, stable, or being fixed
- 45 violations spanning multiple runs with no reduction signal → likely accumulating silently
- Issue-to-pr-loop works better with trend context in the issue body

**Action:** After Step 9L count check, read prior-day count from `subconscious/state/` (or a new `ops/state/metering-violations.json`), compute delta, append trend line to GH #827 comment: "2026-09-22: 45 violations (+N vs yesterday)".

**Impact:** LOW-MEDIUM. Makes Step 9L output actionable. Enables human to see if the violation count is trending up (alarm) vs flat (dormant). Pairs well with issue-to-pr-loop triage.
