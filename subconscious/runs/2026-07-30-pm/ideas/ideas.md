# Candidate Ideas — Run 102 (2026-07-30-pm)

**Evidence basis:** KB stale 7 days (threshold TODAY), Step 9G not in SKILL.md (PR #577 open 6+ days, CI blocked by GH Actions spending limit Day 11+), Step 9H not in SKILL.md (PR #611 open <1 day), governance.json shows total_runs=100 (morning run 101 didn't persist), graph/runtime.py 516 lines (86% of 600-line threshold), sweeper 2 days old.

---

## Idea 1 — Step 9G-Direct: KB Self-Repair With GH Actions Fallback

**Category:** operational  
**Effort:** XS (~30 bash lines in SKILL.md)  
**Evidence:** KB last compile 2026-07-23 (7 days, threshold HIT TODAY). Step 9G (GH workflow run) is cycle-2 carry-forward — PR #577 has been open 6+ days but GH Actions spending limit (Day 11+) prevents CI validation and will also block `gh workflow run` at execution time. The nightly environment has ANTHROPIC_API_KEY and can call `bash scripts/daily/kb-autopopulate.sh` directly.

**What:** Add Step 9G block to `.claude/skills/nightly-commit-review/SKILL.md`. The block:
1. Reuses Step 9F's `DAYS_STALE` variable (already computed above it)
2. Condition: `DAYS_STALE -gt 7`
3. Path A: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify` — if exit 0, sleep 30, check conclusion
4. Path B (fallback when Path A non-zero exit): `bash scripts/daily/kb-autopopulate.sh` directly
5. If both paths fail: comment on GH #403 with specific diagnostic

**Why beats PR #577 Step 9G:** PR #577's Step 9G only has Path A (GH workflow). With spending limit active, that exits non-zero silently. Path B is the insight that makes this immediately load-bearing. KB can be repaired TONIGHT without GH Actions or any PR merge.

**Why now:** KB threshold crossed TODAY. Cycle 2 of 3 carry-forward. At cycle 3, escalation to direct implementation.

**Risk:** LOW. Additive bash block. Script `kb-autopopulate.sh` is proven (ran 2026-07-23, 2026-07-13). Never executes nodes — only compiles knowledge.

---

## Idea 2 — Autonomy Loop Daily Health Check (Step 9I)

**Category:** operational  
**Effort:** S (~25 bash lines)  
**Evidence:** `scripts/autonomy/` infrastructure shipped PR #599 (3 days old) + PR #608 sweeper (2 days old). `run_loop.py list` subcommand available. Sweeper marks stranded runs FAILED. No monitoring hook exists yet.

**What:** Add Step 9I to nightly SKILL.md — run `python3 scripts/autonomy/run_loop.py list` and summarize: total runs, running count, failed count, oldest running age. If any run has been RUNNING >2h (sweeper should have caught it), alert GH #403.

**Why NOT now:** Sweeper shipped 2 days ago. Zero production incident data yet. Monitoring infrastructure before incident data is premature architecture — Karpathy principle "deterministic-first." Wait for a real stranded-run incident to calibrate thresholds. Park in backlog at 3-week review point.

**Parking condition:** Revisit when autonomy loop has >7 days of production data.

---

## Idea 3 — governance.json Active Directions Archive

**Category:** workflow_efficiency  
**Effort:** L (scripting + manual review of 13+ entries)  
**Evidence:** governance.json has 13+ `active_directions` entries, many with `status: pending_human_action` from runs 88-93 (5-8 weeks old). These pollute ideation signal — subconscious considers "pending" ideas as fresh candidates when they've been pending so long they're stale.

**What:** Add an `archived_directions` section to governance.json. Archive any `pending_human_action` entries older than 21 days. Update the subconscious skill to skip archived entries in candidate generation.

**Why NOT now:** L-effort task with no immediate production impact. The stale entries are noise but not causing wrong-direction decisions — they're just skipped when evidence doesn't support them. Real benefit is marginal given the subconscious already weighs evidence. Address in a dedicated governance cleanup session.

**Parking condition:** Revisit when active_directions exceeds 20 entries.

---

## Idea 4 — graph/runtime.py God-Class GH Issue Filing

**Category:** code_health  
**Effort:** XS (file one GH issue)  
**Evidence:** graph/runtime.py is 516 lines (86% of 600-line CLAUDE.md Rule 9 threshold). Morning run set a watch point at 550 lines. No GH issue exists tracking this refactor obligation.

**What:** File GH issue tracking the graph/runtime.py split obligation before it crosses 600 lines. Tag: `code-health`, `refactor`. Link to CLAUDE.md Rule 9. Suggest split: `runtime_core.py` + `node_executor.py` + `checkpoint_manager.py`.

**Why NOT now:** 516 lines is not yet the threshold (600). Morning run correctly set 550 as the check point. Filing an issue before the threshold creates false urgency and would increase the subconscious action queue unnecessarily. The morning digest already tracks this. Trigger: file the issue when `wc -l backend/graph/runtime.py` exceeds 550.

**Parking condition:** 550-line threshold per morning run 101 mandate.

---

## Idea 5 — Paying Tenant Silence Alert via GH Actions Workflow

**Category:** customer_value  
**Effort:** S (~40 lines workflow YAML + query)  
**Evidence:** Morning run filed GH #610 (tenant silence SQL spec). No `paying_tenant_silence.yml` GH Actions workflow exists. Issue #610 tagged `ai-ready`. Three paying tenants (Keys Koffee, Savvy Glamour, Hatch House) — if one goes silent for 7+ days, that's a churn risk.

**What:** Create `.github/workflows/paying_tenant_silence.yml` — runs daily, calls backend API to check last conversation per paying tenant, alerts to GH issue or Slack if any tenant has been silent >7 days.

**Why NOT now:** GH Actions spending limit is Day 11+. Adding a new workflow that runs daily makes no sense while Actions is dark — the workflow can't run and we'd be shipping a broken feature. Block until spending limit resolved (owner action required per morning digest).

**Parking condition:** GH Actions spending limit resolved. Then implement directly (issue #610 already filed with spec).

---

## Summary

| Rank | Idea | Category | Effort | Decision |
|------|------|----------|--------|----------|
| 1 | Step 9G-Direct KB Self-Repair | operational | XS | **WINNER** |
| 2 | Autonomy Loop Step 9I Health Check | operational | S | Parked — too new |
| 3 | governance.json Archive | workflow_efficiency | L | Parked — not urgent |
| 4 | graph/runtime.py GH Issue | code_health | XS | Parked — threshold not hit |
| 5 | Tenant Silence GH Workflow | customer_value | S | Parked — GH Actions dark |
