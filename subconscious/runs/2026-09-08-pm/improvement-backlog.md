# Improvement Backlog — Run 118 (2026-09-08-pm)

## Parking Lot (strong ideas, not this run's winner)

### P1: Extend `from __future__` CI to all backend/*.py
- **Evidence:** `pr-check.yml:121` and `health-check.yml:58` both scope to `backend/routers/` only. Issues #805 (service files, 1d) and #823 (5 test files, today) on consecutive days. Pre-commit hook covers edits but not API pushes or hook-bypass commits.
- **Action:** 1-line change per YAML: `backend/routers/` → `backend/`. File as GH issue or implement directly in a CI-only PR.
- **Why not this run:** Winner is governance-mandated; runner-up is next in line.
- **When to ship:** Next PR touching CI config, OR next nightly that finds another `__future__` annotation outside routers/.

### P2: Step 9J Token Budget Diagnosis
- **Evidence:** 17/19 Dependabot PRs skipped in runs 115-117 (3-run pattern). Security patches aging 40+ days.
- **Blocked by:** No nightly transcript available to confirm root cause. "Token budget" is hypothesis — Step 9J implementation could have its own filter logic or loop cap.
- **Action needed first:** Read Step 9J block in nightly-commit-review/SKILL.md + last 3 nightly transcripts. Confirm budget vs. logic root cause. Then prescribe fix (reorder OR code change).
- **When to revisit:** Run 119 — include Step 9J nightly transcript excerpt in evidence.

### P3: Document React 19 Hold Decision
- **Evidence:** PRs #586/#591/#593 stale 43d, no ADR, no issue explanation. Dependabot keeps re-proposing.
- **Action:** Add entry to `docs/dev-knowledge/architecture-decisions.md` explaining hold. Close PRs with link.
- **Category:** Human decision, not autonomous subconscious scope. Low urgency; reduces clutter.

## Killed Ideas (not relevant to subconscious)

### Consolidate meter-ai-endpoint PRs (#821, #824, #825)
- **Reason:** Pure human operational task. Subconscious doesn't close/supersede PRs. Human reads morning digest, acts.
- **Status:** Morning digest already flagged this as Priority 2.

## Governance Signals for Run 119

1. **Verify god class GH issue filed.** If `refactor(m8): split os_tool_executions.py` issue NOT present in GH, escalate to subconscious-direct file.
2. **Check if CI fix for `from __future__` scoping merged.** If not, promote to run 119 winner candidate.
3. **Gather Step 9J transcript.** Read the nightly-commit-review nightly transcript excerpt — confirm whether 17/19 skip is budget or code logic.
4. **Check #801 (P0 approve_send_once).** If still open at run 119, flag to owner.
5. **Check Step 9L first results.** Nightly ran 2026-09-08 but Step 9L (PR #804) may have landed after the run. Check if Step 9L violation reports appear in run 2026-09-09 nightly log.
