# Ideas — Run 117 (2026-09-06-pm)

## Evidence Digest
- `check_ai_metering.py` shipped commit `1c5b749` with 325 lines of tests — finds **30+ unguarded AI-calling functions** across routers + services
- Step 9L SKILL.md block: ABSENT (grep=0 confirmed this run)
- `os_tool_executions.py`: 783L, 8+ days stable since `f22ef04`
- Step 9G trigger broken in cloud sessions (gh CLI unavailable) — KB 10+ days stale
- Step 9J: 17/19 Dependabot PRs still skipped per token-budget failure (unchanged from run 115)
- M9 sprint landing fast: shadow_planner.py, billing_staging_smoke.py, website-connect preflight all shipped this week

---

### Idea 1: Step 9L SKILL.md block (carry-forward, 2nd cycle)
**Evidence:** `check_ai_metering.py` confirmed working this run — outputs 30+ violations (routers: bids.py, content.py, jobs.py, menu.py, onboarding.py×3, os_files.py, platform_support.py, reviews.py, snippets.py, social_media.py×2; services: orchestrator.py, scheduled_jobs_ext.py, bot_health.py, content_repurposer.py, conversation_enrichment.py, inbox_triage.py×2, instant_kb.py, kb_from_text.py, kb_reranker.py, local_seo_ai.py×3). governance `autonomous_executable_run: 117` mandate active.
**Action:** Add Step 9L block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9K. Run `python3 scripts/check_ai_metering.py`, parse output, dedup-check against open GH issues, file issues (labels: `billing`, `ai-ready`). Log: `Step 9L: {N} functions checked, {M} violations, {K} issues filed, {D} dedup-skipped`.
**Impact:** 30+ billing exposure gaps filed as ai-ready GH issues. Every future unguarded AI route caught within 24h of landing. Prevents next 7-PR emergency retrofit sprint.
**Category:** code_health

---

### Idea 2: Step 9G cloud fix — replace gh CLI with mcp__github__actions_run_trigger
**Evidence:** KB 10+ days stale (last compile 2026-08-26 per log.md). Step 9G trigger fails silently in cloud sessions — gh CLI unavailable. `mcp__github__actions_run_trigger` is available in deferred tools and works in nightly sessions (same GitHub MCP server). Step 9G trigger never fires → no workflow run → no diagnostic comment on GH #403.
**Action:** Edit Step 9G in `.claude/skills/nightly-commit-review/SKILL.md`: replace `gh workflow run kb-autopopulate.yml` shell command with `mcp__github__actions_run_trigger(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml")`. Add 30s status check via `mcp__github__actions_list`. Comment on GH #403 with run URL on failure.
**Impact:** KB self-healing trigger fires instead of silently failing. When ANTHROPIC_API_KEY is added to GH Actions (GH #403), KB auto-heals within 24h. Even now: produces diagnostic workflow run URL in GH #403 comment.
**Category:** operational

---

### Idea 3: os_tool_executions.py god class split
**Evidence:** 783 lines, 8+ days stable (last commit `f22ef04` Billing Automation v1). Rule 9 threshold (600L) exceeded by 30%. M9 sprint actively adding os_workflows/ code — each PR risks touching this file. Governance confirmed as run 117 split candidate since run 115.
**Action:** Split `backend/services/os_tool_executions.py` (783L) into: `os_tool_execution_store.py` (DB CRUD, ~200L), `os_tool_executor.py` (execution logic, ~250L), `os_tool_approval_handler.py` (approval/rejection flows, ~200L). Update imports in `backend/routers/os_tool_executions.py` and tests.
**Impact:** Each module <300L. Future M9 PRs touch only the relevant module — smaller diffs, easier review, lower blast radius. Matches Rule 12 (new files over bloat).
**Category:** code_health

---

### Idea 4: Step 9J token-budget fix — move Step 9J earlier in nightly
**Evidence:** Step 9J checked 19 Dependabot PRs but skipped 17/19 due to token budget — confirmed runs 115 and 116 (unchanged). Root cause: Step 9J runs late in a 500-step nightly session after Steps 9A-9K exhaust the budget. 19 PRs waiting — CVE window extends with each skip.
**Action:** Reorder SKILL.md steps: move Step 9J immediately after Step 9B (quick pre-condition check), before the heavier Steps 9C-9I. Or add a lightweight `max_prs_per_run` counter guard that skips Steps 9C-9I when Dependabot PR count > N to preserve budget for Step 9J.
**Impact:** All 19 Dependabot PRs inspected each nightly run. CVE patches land within 24-48h of CI passing. Eliminates 2-week lag.
**Category:** workflow_efficiency

---

### Idea 5: check_ai_metering.py added to pr-check.yml (advisory gate)
**Evidence:** `check_ai_metering.py` ships with 325 lines of tests and confirmed working. 30+ violations exist in current codebase. Every new PR risks adding more unguarded AI calls. pr-check.yml runs on every PR but has no AI-metering gate.
**Action:** Add `python3 scripts/check_ai_metering.py` as an advisory (warning-only) step to `.github/workflows/pr-check.yml`. Log output to PR annotations. Do NOT fail CI on existing violations — use `--diff-only` flag (new files only) or a suppression allowlist.
**Impact:** New unguarded AI routes caught at PR time, not nightly. Zero tolerance for new violations while existing ones are triaged.
**Category:** code_health
