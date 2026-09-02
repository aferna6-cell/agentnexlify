# Ideas — Run 115 (2026-09-02-pm)

## Evidence Digest

- **Step 9K PASS**: nightly-2026-09-01 confirmed "9K: 3 stale subconscious PRs (30-35d), below comment threshold". nightly-2026-09-02 shows 4 stale, still under threshold. Both runs fired correctly.
- **Step 9J AMBIGUOUS**: fired 2026-09-01 (rebased #721 and #722), then "9J Dependabot: skipped" on 2026-09-02 with no diagnostic context. Unknown whether skip is correct (0 PRs remain) or detection failure.
- **os_tool_executions.py NOT stable**: 2 commits since 2026-08-30 (M8 close fixes). 4d+ clean window needed before god-class split is safe.
- **SUPABASE_ACCESS_TOKEN still unset** in Railway — GH #684 open 40+ days. Brain connector dead, KB autopopulate dead.
- **M8 fully closed**, M9 started: M9.1 workflow contract merged (PR #751), M9.2 persistence engine next.
- **bug-patterns.md**: "Silent-green automation" — Keys Koffee paying tenant's widget missing 5+ weeks, nobody noticed. Prevention: heartbeat distinguishing "ran and found nothing" from "never ran".

---

### Idea 1: Step 9J Diagnostic Enhancement
**Evidence:** nightly-2026-09-02 shows "9J Dependabot: skipped" with no further detail. Three consecutive nightly logs (2026-09-01 triggered, 2026-09-02 skipped) create ambiguity: correct skip (0 PRs remain after rebase) or regression in detection. No way to distinguish from log alone.
**Action:** Add a log line to Step 9J in `.claude/skills/nightly-commit-review/SKILL.md` that fires BEFORE the skip decision: "Step 9J: N Dependabot PRs found via search_pull_requests". If N=0, skip is correct; if N>0, skip is a bug.
**Impact:** Closes 3-run ambiguity. Future runs self-diagnose. ~3-line SKILL.md edit. Autonomous-executable.
**Category:** workflow_efficiency

---

### Idea 2: os_tool_executions.py God Class Split
**Evidence:** File is 775 lines (>600 threshold per user-rules.md Rule 9). 3 distinct concerns: (1) persist tool execution rows, (2) apply internal writes (notes onto leads), (3) approve/reject parked actions. Run 114 mandate item 5 specifically flagged this as a candidate once stable.
**Action:** When stability threshold met, split into `os_persist.py` (rows), `os_apply.py` (writes), `os_approval.py` (park/approve/reject). Rename imports across callers.
**Impact:** Each file drops to ~200-250 lines. Cleaner blast radius for M9.2 persistence engine changes.
**Category:** code_health
**Blocker:** 2 commits since 2026-08-30 — NOT stable. 4d+ clean window needed.

---

### Idea 3: Step 9L — Per-Tenant Widget Health Alert
**Evidence:** bug-patterns.md documents "Silent-green automation" (Keys Koffee case) — widget missing 5+ weeks, no alert. Prevention is a heartbeat check. Nightly is the right cadence.
**Action:** Add Step 9L to nightly-commit-review SKILL.md: query `widget_configs` for tenants last active >7d, file weekly GH issue listing them.
**Impact:** Catches silent widget disconnects before tenants churn.
**Category:** operational
**Blocker:** Supabase MCP unavailable in headless/nightly sessions (confirmed run 88). Mechanism is blocked.

---

### Idea 4: M9.2 Schema Migration Guard
**Evidence:** M9.1 workflow contract merged (PR #751). M9.2 persistence + deterministic engine is next. Schema sketch exists at `specs/m9-workflow-schema-sketch.sql`. No migration filed yet.
**Action:** File `migrations/NNN_m9_workflow_state.sql` following the schema sketch before M9.2 backend work starts, ensuring the DB side precedes service changes.
**Impact:** Prevents "half migration" anti-pattern (user-rules.md Rule 8). M9.2 can reference real columns.
**Category:** workflow_efficiency
**Note:** Implementation work, not a subconscious recommendation. Subconscious recommends → human executes.

---

### Idea 5: SUPABASE_ACCESS_TOKEN Railway Escalation
**Evidence:** GH #684 open 40+ days. Brain connector dead, KB autopopulate dead. nightly-2026-09-01 confirms "9C: brain connector 40d stale → commented on GH #684". The credential is simply not set in Railway environment variables.
**Action:** Add Step 9M to nightly SKILL.md: if brain connector stale >7d, post escalating comment to GH #684 AND add a PR description note to the next open subconscious PR linking this blocker.
**Impact:** Forces visibility on a 40-day-stale credential that is blocking KB features.
**Category:** operational
