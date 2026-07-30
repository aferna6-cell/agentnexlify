# Ideas — Run 101 (2026-07-30)

## Evidence Digest

- **KB stale 7 days** (last run 2026-07-23) — Step 9F threshold crossed today; Step 9G NOT in SKILL.md (carry-forward 1st cycle from run 100)
- **GH Actions spending limit** (#500): 11+ days as of 2026-07-30, ALL CI red, ALL PRs blocked, dependabot stalled — morning digest 2026-07-29 flagged as DAY 9 #1 priority
- **Agent graph runtime + autonomy sweeper** shipped: 43 files / 10,839 lines (PR #599), sweeper 152 lines / 422 tests (PR #608), migration 189 live — major new system
- **Nightly CLEAN**: 2 consecutive quiet days (ops logs only)
- **Bug pattern documented**: silent-green tenant outage — Keys Koffee widget dark 5+ weeks, zero automated detection (bug-patterns.md 2026-07-23)
- **graph/runtime.py**: 516 lines (86% of 600-line god-class threshold, actively developed)

---

### Idea 1: Step 9H — GH Actions CI Systematic Failure Alerter
**Evidence:** GH Actions spending limit blocked ALL CI for 11+ days. Morning digest called it DAY 9 #1 priority. No automated detection exists — discovered manually. Steps 9B/9C/9D/9E/9F/9G all use proven SKILL.md bash block mechanism. Next occurrence (different org, different spending limit event) will be silent until manually found again.
**Action:** Add Step 9H bash block to nightly-commit-review SKILL.md: check if ALL major workflows have 0 successes in last 48h (`gh run list --limit=20` scan); if universal failure detected, file GH issue with labels `human-action-required` + `infra` titled `INFRA: GH Actions systematic failure — check billing/spending limit`.
**Impact:** Future GH Actions billing outages caught within 24h instead of 11+ days. CI blindspot closed.
**Category:** operational

---

### Idea 2: Step 9G Carry-Forward — Escalate PR #577 Merger (Bonus A candidate)
**Evidence:** KB at 7-day threshold today (2026-07-30). PR #577 (Step 9G) has been DRAFT for 8 days, not merged. Morning digest 2026-07-29 noted "KB threshold hits tomorrow" and "safe to merge even with red CI (SKILL.md only)." Step 9F fired staleness alert on nightly-2026-07-22; Step 9G needed to trigger self-repair.
**Action:** Post escalation comment on PR #577 noting KB threshold crossed today, PR is SKILL.md-only (safe to merge without CI), and Step 9G self-heal will fire within 24h of merge.
**Impact:** Step 9G merged; KB self-healing operational within 24h. Prevents next multi-day stale window.
**Category:** operational

---

### Idea 3: Autonomy Loop Daily Health Check
**Evidence:** Sweeper shipped 2026-07-29 (#608), 24h ago. Major new system: `backend/graph/` (43 files, 10,839 lines), `scripts/autonomy/` (8 scripts), migration 189. Only 1 known crash (run a82c9f38). `run_loop list` exists as CLI but only runs manually. No automated daily signal on stranded run count.
**Action:** Add nightly bash block calling `python3 scripts/autonomy/run_loop.py list`; log stranded count; if >0, call `run_loop.py sweep --dry-run` and log candidates; file GH issue if sweep would change state.
**Impact:** Stranded autonomy runs detected and flagged within 24h of crash; sweeper dry-run confirms candidates before human action.
**Category:** workflow

---

### Idea 4: Paying Tenant Silence Alerter
**Evidence:** bug-patterns.md 2026-07-23: "Silent-green automation: paying tenant's widget missing for 5+ weeks, nobody noticed." Fix pattern explicitly documented: "tenant-level outcome metrics (conversations/7d) alert on zero for paying tenants." No implementation exists. With 3 tenants, one silent for 5+ weeks = 33% ARR at churn risk.
**Action:** File GH issue with `human-action-required` + `revenue` labels containing copy-paste SQL to add to a scheduled monitoring job: `SELECT client_id, COUNT(*) as convos FROM conversations WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY client_id` — alert if a known paying tenant has 0 rows.
**Impact:** Next per-tenant outage caught within 7 days instead of 5+ weeks. Retention and revenue protection.
**Category:** operational

---

### Idea 5: graph/runtime.py God-Class Pre-Emption
**Evidence:** `backend/graph/runtime.py` is 516 lines (86% of 600-line threshold from user-rules.md Rule 9). PR #599 added this file as part of a 10,839-line addition; the system is actively developed. At current pace (autonomy sweeper, budget module, checkpoint module all already separate), the runtime could absorb new responsibilities as the system grows.
**Action:** Add wc-l check for `backend/graph/runtime.py` to nightly SKILL.md: if >550 lines, log warning + file GH issue suggesting split into `runtime_core.py` (graph execution) / `runtime_recovery.py` (error/retry) / `runtime_budget.py` (budget management).
**Impact:** Prevents next god-class before it accumulates; preserves modular architecture of the autonomy system.
**Category:** code_health
