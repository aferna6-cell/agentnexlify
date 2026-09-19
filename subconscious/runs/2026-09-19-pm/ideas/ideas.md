# Ideas — Run 2026-09-19-pm (Run 125)

Generated from evidence: 3 days of git history, nightly-2026-09-19, mandate check from run 124.

---

### Idea 1: Step 9G SKILL.md Fix — Replace broken `gh` CLI with mcp__github__actions_run_trigger
**Evidence:** nightly-2026-09-19 confirms: "Step 9G still uses broken `gh` CLI command." `mcp__github__actions_run_trigger` = 0 hits in SKILL.md Step 9G block (grep). In-session MCP workaround applied 2026-09-18 (status 204 success) but does NOT persist — each nightly session re-runs broken code. KB 24d stale; Step 9G is the self-healing mechanism; it's broken. Run 121 mandate set autonomous-executable at run 124; this is run 125 — 1 run past threshold. Task prompt = recommend-only.
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9G block: replace `gh workflow run kb-autopopulate.yml` bash command with `mcp__github__actions_run_trigger({owner: "aferna6-cell", repo: "agentnexlify", workflow_id: "kb-autopopulate.yml"})` MCP call. Same logic: check exit/status, comment on GH #403 on failure, log SUCCESS line.
**Impact:** KB self-healing resumes permanently on every nightly. 24d-stale KB unblocked. Step 9G goes from silently failing to working.
**Category:** workflow_efficiency

---

### Idea 2: Step 9E P0 Tier — Add 10-Day P0 Escalation to credential expiry (6th carry-forward)
**Evidence:** AUTOPILOT_GH_TOKEN expires 2026-10-02 (13 days). P0 fires at ≤10 days → 2026-09-22 (3 days away). `days_remaining` = 0 hits in SKILL.md, `P0` = 0 hits. 5 consecutive carries (runs 119-124). Autonomous-executable threshold reached at run 122. GH #399 = 7+ autonomous comments, 0 human responses. Task prompt = recommend-only (same block as runs 122-124).
**Action:** Edit Step 9E SKILL.md block: after existing ≥76d warning comment logic, add: if `days_remaining ≤ 10`, file a NEW GH issue with labels `human-action-required + ops + P0` (not a comment on #399) with body naming the expiring credential, expiry date, and automation systems at risk. Dedup: skip if a P0 issue for this credential already open.
**Impact:** P0 alert fires 2026-09-22. New GH issue surfaces in P0 dashboard view (distinct from #399 thread noise). Prevents silent automation death 2026-10-02.
**Category:** operational/workflow_efficiency

---

### Idea 3: Dependabot Major-Version Triage GH Issue
**Evidence:** nightly-2026-09-19: 5 Dependabot PRs open, all skipped as major-version bumps (react 18→19 in demo-platform, react 18→19 in frontend, vitest 4→5 in frontend, mcp >=2.2.0). Step 9J correctly skips major bumps but there is NO GH issue tracking them for manual review. CVE window accumulates silently. react 19 and vitest 5 are stable releases (not breaking for most usage patterns). Each day without review = unpatched security surface.
**Action:** File one GH triage issue listing all 5 major-version Dependabot PRs with PR numbers, package names, and versions. Label: `dependencies + human-action-required`. Body: 4 of 5 may be safe to merge (react 18→19 in demo-platform is non-production). Request manual review.
**Impact:** Creates human accountability for aging major-version dependencies. Closes the Step 9J gap (auto-merge for minor, human-triage for major).
**Category:** operational

---

### Idea 4: AI Metering Violation Trend Tracking (Step 9M Draft)
**Evidence:** Step 9L confirmed: rc=2, 45 violations. GH #827 open. No trend data exists — violations were 45 in run 120, run 121, run 122, run 123, run 124 (unchanged). Is the metering effort stalled or is active work happening? A trend signal (stored violation count per nightly run) would distinguish "no new violations added" from "violations never fixed." Run 122 nightly memo: "Step 9L: detector rc=2, 45 violations." Same every day.
**Action:** Add Step 9M block to nightly SKILL.md: read previous violation count from `subconscious/state/ai-metering-trend.json`; compare to today's Step 9L rc=0 count; compute delta; update file; log `Step 9M: {today} violations, {delta:+N} vs yesterday`. If delta > 0: new violations added — warn. If delta < 0: progress — celebrate. If unchanged: neutral.
**Impact:** Distinguishes "stagnant" from "progressing." Catches regression immediately if new unguarded AI calls land.
**Category:** code_health/observability

---

### Idea 5: os_tool_executions.py God-Class Split Planning
**Evidence:** Service = 783L, Router = 436L. 6th consecutive subconscious mention. GH issue reportedly filed as bonus action in run 123. Run 116 described it as "god class split (783L service + 411L router)" and run 97 as "stable at 783L." The file has been stable for 7+ days (no commits since f22ef04 ~2026-08-30). God-class splitter SKILL.md exists (.claude/skills/god-class-splitter/SKILL.md). Need a concrete split plan before execution.
**Action:** Read os_tool_executions.py to identify the 3-4 natural concerns (execution, routing/dispatch, state/history, result-processing). Write a brief split plan: proposed new service file names, lines moved, test implications. File as implementation sketch comment on the GH issue if one exists.
**Impact:** Unblocks the split. God classes are where bugs compound — 1219L file = high blast radius on any future change.
**Category:** code_health
