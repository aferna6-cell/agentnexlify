# Run 102 — Candidate Ideas
**Date:** 2026-08-08-pm
**Evidence sources:** nightly logs (2026-08-07, 2026-08-08), bug-patterns.md, customer-gaps.md, governance.json, memory.jsonl, orchestrator.py:238/319

---

## Idea 1 — Nightly Detached-HEAD Branch Guard

**Category:** operational
**Evidence:** Two consecutive nightly sessions (2026-08-07 and 2026-08-08) ran with HEAD detached from `refs/heads/main`. Commits `97e1044`, `cbbaae5`, `7dff08b` were orphaned and never pushed. GH #640 was incorrectly closed. The 2026-08-08 nightly had to re-discover and re-apply the same fix. This is the first confirmed back-to-back orphaned-commit failure.

**Root cause (hypothesized):** Automated session starts from a detached ref (scheduled trigger or GitHub Actions clone behavior). Before any commit, there is no check that HEAD is on a named branch.

**Action:** Add 3-line guard at top of `scripts/daily/nightly-commit-review.sh` (and any other nightly script that commits):
```bash
if git symbolic-ref HEAD >/dev/null 2>&1; then
  echo "HEAD on branch: $(git symbolic-ref --short HEAD)"
else
  echo "ERROR: HEAD detached. Checking out main." && git checkout main
fi
```
Also add `git status --short` and `git symbolic-ref HEAD` to the nightly log header so every future run self-reports its HEAD state.

**Impact:** Prevents fix-orphaning. Low risk — bash-only change to a script, not production code.
**Effort:** XS (10-line bash edit)
**Reversible:** Yes
**Channel:** `autonomous_executable` (existing-file patch)

---

## Idea 2 — KB Autopopulate `continue-on-error` Silent-Failure Fix

**Category:** operational
**Evidence:** `kb-autopopulate.yml` uses `continue-on-error: true`, causing the workflow to report `conclusion: success` even when ANTHROPIC_API_KEY / VOYAGE_API_KEY / SUPABASE_ACCESS_TOKEN are missing. Nightly 2026-08-07 log confirmed: runs #269-#271 all show `conclusion: success` but KB log has no entries since 2026-07-23. Step 9G fires and queues the workflow correctly, but the workflow silently succeeds without actually populating the KB. GH #403 documents the history.

**Root cause:** `continue-on-error: true` on the KB compile step swallows exit codes. Designed for resilience; has become a blind spot.

**Action:** Remove `continue-on-error: true` from the compile step in `kb-autopopulate.yml`. Add an explicit secret-presence check step that fails fast with a human-readable message if any required secret is missing. Update Step 9G in `.claude/skills/nightly-commit-review/SKILL.md` to check `conclusion: failure` and file GH issue on failure rather than just reporting "queued."

**Impact:** KB freshness restored. Eliminates silent failures. Future Step 9G runs will correctly detect and alert.
**Effort:** S (2-file YAML + MD edit)
**Reversible:** Yes
**Channel:** `autonomous_executable` (existing-file patch, both files exist)

---

## Idea 3 — Orchestrator Grandfathered Plan Gap

**Category:** code_health
**Evidence:** `backend/services/automation/orchestrator.py:238` and `:319` both check `if plan in ("professional", "enterprise", "agent_os"):` for branded email wrapping. The grandfathered plans `growth` and `autopilot` are absent. Every other canonical plan-gate file (`agent_os_gate.py`, `plan_gate.py`, `ai_usage_guard.py`) includes the full set. Per CLAUDE.md: "Legacy/grandfathered (still honored on old contracts): `growth`, `autopilot`, `professional`, `enterprise`." Tenants on `growth` or `autopilot` are silently sending unbranded emails from automations.

**Action:** Add `"growth", "autopilot"` to both plan tuples in orchestrator.py:238 and :319. Two 1-line edits, no migration, no schema change.

**Impact:** Fixes silent customer-facing defect for any remaining `growth`/`autopilot` contract tenants. Direct revenue risk: branded emails are a plan entitlement; missing them is a broken promise.
**Effort:** XS (2 lines in 1 file)
**Reversible:** Yes
**Channel:** `autonomous_executable`

---

## Idea 4 — Per-Tenant Conversation Zero-Alert

**Category:** customer_value / operational
**Evidence:** Bug-patterns.md (2026-07-23 entry): "Keys Koffee had 5+ weeks of zero conversations — a paying tenant, widget dropped, no system flagged it." No per-tenant heartbeat exists. The pattern generalizes: any tenant whose widget embed breaks silently disappears from conversations without triggering an alert.

**Action:** Add a nightly cron query (can live inside the existing daily health check in `scripts/daily/`) that finds any paying tenant (`plan = 'chatbot' OR 'agent_os'`) with zero conversations in the past 7 days. File a GH issue or send an internal alert email via Resend.

**Impact:** Prevents 5-week-silent-outage class of customer churn. High customer value. Medium effort (new script + cron entry).
**Effort:** M (new script, new cron, internal email via existing Resend setup)
**Reversible:** Yes
**Channel:** requires new file creation — not `autonomous_executable`, needs human implementation

---

## Idea 5 — Step 9H: Subconscious PR Pile Alerter

**Category:** workflow_efficiency
**Evidence:** Run 101 memory: "15 open PRs, 7 subconscious drafts." Run 102 governance mandate: "PR pile-up (#625/#626/#613/#611/#606)." Subconscious generates PRs faster than the owner can merge them. No existing step alerts on pile-up. The PR dedup guard (run 99) prevents duplicate branch creation but doesn't address the backlog.

**Action:** Add Step 9H to `.claude/skills/nightly-commit-review/SKILL.md`: if open subconscious draft PRs > 3, post a single GH comment on the oldest open subconscious PR summarizing the pile ("N subconscious PRs pending — oldest is X days") and send a push notification. No new PRs from subconscious until pile drops below threshold.

**Impact:** Prevents PR debt. Forces owner attention before backlog grows unmanageable.
**Effort:** S (SKILL.md edit)
**Reversible:** Yes
**Channel:** `autonomous_executable` (SKILL.md block addition)
