# Run 115 Ideas — 2026-09-03-pm

## Evidence Digest

- Migrations 196 (os_tool_executions status CHECK tighten) and 197 (L2 idempotency for double-invoice prevention) both marked "NOT YET APPLIED" in schema-log.md while Billing Automation v1 (f22ef04, os_invoice_actions.py 650L) shipped today using the same table. Race condition: a double-invoice send can occur before 197 is applied.
- Nightly-2026-09-03: Step 9J fired correctly (19 Dependabot PRs found, 2 rebases triggered on #721/#722). Step 9K fired correctly (1 subconscious PR #753 at 1d old, under 3d threshold — no action). Both steps healthy.
- engine.py (M9.2) has dead code in `derive_workflow_status()`: inner guard `if all(s != "failed" and s != "unknown" for s in states)` is always True when outer condition restricts states to `{"succeeded", "cancelled"}`. Nightly flagged LOW, deferred.
- No Step 9L (unapplied migration alerter) in nightly-commit-review SKILL.md.
- GH #684: SUPABASE_ACCESS_TOKEN missing — brain connector 42 days stale. Pure human action.
- planner_bakeoff.py at 976L (god-class threshold exceeded) but last commit today (fdcbb97) — not stable for split.

---

### Idea 1: Step 9L — Unapplied Migration Nightly Alerter
**Evidence:** schema-log.md shows migrations 196 and 197 both "NOT YET APPLIED". Migration 197 adds L2 idempotency to prevent double-invoice sends. Billing Automation v1 (f22ef04) shipped today using os_tool_executions table — the exact table migration 196 governs. Risk window is open. No automated detection exists. Proven pattern: Steps 9F through 9K all added autonomous SKILL.md steps that caught exactly these kinds of silent gaps.
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` — add Step 9L block that greps `docs/dev-knowledge/schema-log.md` for "NOT YET APPLIED", counts matches, and posts/updates a GH issue labeled `human-action-required` + `database` when count > 0. Dedup guard: check if issue already open before creating. Cap comments at 1 per nightly run per issue.
**Impact:** Catches all future unapplied migration risks automatically. Prevents billing double-send and other data integrity bugs from slipping into production undetected. Autonomous-executable SKILL.md edit (no human approval needed).
**Category:** workflow_efficiency

---

### Idea 2: Fix M9.2 Dead Code in derive_workflow_status()
**Evidence:** nightly-2026-09-03 flagged `engine.py` `derive_workflow_status()` inner guard as dead code (LOW severity, deferred). Outer condition filters states to `{"succeeded", "cancelled"}`; inner `if all(s != "failed" and s != "unknown" for s in states)` is always True in that context. Not behavioral but a readability trap for future M9 engineers.
**Action:** Edit `backend/services/os_workflows/engine.py` — remove the redundant inner guard (2-line diff). No logic change; the `return "completed"` path is unconditionally reached.
**Impact:** Cleaner M9 codebase. Removes future reviewer confusion about invariants. Low risk.
**Category:** code_health

---

### Idea 3: File GH Issue for Migrations 196/197 Unapplied Risk
**Evidence:** schema-log.md entries for 196 and 197 both say "NOT YET APPLIED". f22ef04 Billing Automation v1 just shipped today, using os_tool_executions. Migration 197 prevents double-invoice sends via L2 idempotency — this is a billing correctness risk, not a theoretical one.
**Action:** Create GH issue titled "fix(migrations): apply migrations 196 + 197 — unapplied while billing automation is live" with labels `human-action-required`, `database`, `revenue`. Body: exact migration filenames, risk description, apply command.
**Impact:** Creates human-visible paper trail. Can be manually actioned. But goes into stalled queue (GH #399 blocking issue-to-pr-loop).
**Category:** operational

---

### Idea 4: Step 9M — Env-var / Connector Staleness Watchdog
**Evidence:** GH #684 (SUPABASE_ACCESS_TOKEN missing, brain connector dark) has been open 42 days with no resolution. Similar pattern to past credential expiry issues. No automated escalation exists for stale env-var issues.
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` — add Step 9M that searches open GH issues containing "ACCESS_TOKEN" OR "expired" OR "stale connector" older than 30 days, and posts a daily escalation comment until resolved or closed. Cap at 1 comment per issue per 24h.
**Impact:** Prevents brain connector / token issues from sitting silently for months. But: GH #684 requires direct human action (set env var in Railway/Vercel). Automation can only nag; it can't fix.
**Category:** workflow_efficiency

---

### Idea 5: Governance.json active_directions Pruner
**Evidence:** governance.json is 1983 lines, with active_directions and parking_lot arrays holding 100+ entries spanning runs 1–114. Many are `"implemented": true` or superseded. File parse time grows linearly; readability degrades.
**Action:** Add a quarterly governance.json maintenance step: archive all `"implemented": true` entries from active_directions and parking_lot to `subconscious/state/archives/active-directions-pre-YYYY-MM.json`, leaving only last 10 + non-implemented entries. Update `subconscious/state/governance.json` to reference archive.
**Impact:** Governance.json under 500 lines. Faster parse in future runs. But: low urgency — no current bug caused by file size; pure operational hygiene.
**Category:** operational
