# Debate Log — Run 115 (2026-09-01)

Top 3 ideas debated: Idea 1 (Haiku CRM guard), Idea 2 (Step 9K extension), Idea 3 (Step 9L M8 tracker).
Ideas 4 and 5 eliminated at ideation (4: existing mechanism works; 5: stability condition not met).

---

## Idea 1 — Haiku CRM field-omission guard at _extract.ts

### Challenge round
**Adversary:** Two PRs in 2 days is a small sample. PRs #726/#727 fixed admin_records_actions.ts, not _extract.ts — maybe the backfill IS the right fix (defensive coding at the consumer layer). Adding a guard at extraction adds coupling between _extract.ts and the specific requirements of CRM intents. What if non-CRM intents also go through _extract.ts? A blanket guard could break them.

**Defend round**
_extract.ts is intent-typed — it returns typed extraction results per intent class. A CRM intent extraction can enforce its own field contract without touching other intent types. The backfill approach in admin_records_actions.ts is a band-aid that will accumulate: run 115 sees #727 one day after #726 — same class, different field. The next missing field will be a #728. Fixing at extraction time terminates the recurrence. Filing a GH issue (not direct implementation) means a human approves the guard contract before it ships — zero risk to the running system today.

**Evidence check**
- PRs #726 (#726) and #727 (next day) — confirmed same bug class, different fields
- admin_records_actions.ts:427 lines (healthy by Rule 9's 600L threshold) but accumulating backfill logic each run
- _extract.ts is the correct semantic layer for field validation (extracts → validates → passes to action handler)
- GH issue with ai-ready label → issue-to-pr-loop picks it up when AUTOPILOT_GH_TOKEN valid

**Verdict: SURVIVES → WINNER**
Strongest evidence (2 bugs same class, 2 days). Correct layer identified. Bounded effort. No production risk today (GH issue only). Recurrence-terminating.

---

## Idea 2 — Step 9K extension: auto-close implemented subconscious PRs

### Challenge round
**Adversary:** Step 9K just launched. Run 114 implemented it; run 115 is the first verification run. Extending Step 9K now is premature — we don't yet know if the baseline audit is stable. Cross-referencing governance.json from nightly-commit-review SKILL.md introduces fragile coupling: the nightly would need to parse governance.json and match PR titles to active_directions entries by fuzzy string match. One governance.json format change breaks the auto-close logic. Also, closing a subconscious PR prematurely (if governance.json is wrong about status) loses the PR's context.

**Defend round**
The coupling concern is real. Step 9K today only counts — it doesn't cross-reference governance.json. Adding cross-referencing requires trust that governance.json is the canonical truth, but governance.json is updated by each subconscious run, not by a verified CI check. There's legitimate risk of stale governance data triggering incorrect auto-closes.

**Evidence check**
- Step 9K ran clean (3 PRs, 30-35d, below threshold) — confirms baseline works
- But: no evidence of auto-close need yet (3 PRs is manageable, none critical)
- Governance.json-to-PR matching would require fragile title string matching
- 1 run of Step 9K data is insufficient to justify extension

**Verdict: WEAKENED → parking lot**
Mechanism risk is too high at this stage. Re-evaluate after Step 9K has run 5+ times and established reliability baseline. Governance.json-to-PR coupling design needs separate design pass.

---

## Idea 3 — Step 9L: M8 deploy HOLD tracker in nightly

### Challenge round
**Adversary:** M8 HOLD is a transient deployment state. Nightly already tracks deploy status via existing steps. Adding Step 9L for a single transient milestone creates a permanent nightly step that will be a no-op or misleading log entry once M8 deploys. Nightly SKILL.md should not accumulate single-milestone trackers.

**Defend round**
HOLD has persisted multiple runs. If it becomes a recurring pattern (each M-series milestone gets a HOLD), a dedicated tracker makes sense. But "multiple runs" of a 2026-08 sprint is still too short a window.

**Evidence check**
- M8 HOLD mentioned in run_114_mandate — 1 mandate item, no repeat failure pattern
- Existing nightly steps don't track M8 specifically, but no evidence nightly tracking of M8 would change human behavior
- 0 prior Step 9x implementations have been for transient sprint states

**Verdict: KILLED**
Transient concern, no recurrence pattern established, adds permanent step for a short-lived state. M8 will resolve organically. No persistent nightly mechanism warranted.

---

## Summary
| Idea | Verdict |
|------|---------|
| 1 — Haiku CRM field-omission guard (_extract.ts GH issue) | WINNER |
| 2 — Step 9K extension: auto-close implemented PRs | Parking lot (too early, mechanism risk) |
| 3 — Step 9L: M8 HOLD tracker | KILLED |
| 4 — Step 9C SUPABASE_ACCESS_TOKEN escalation | Eliminated at ideation (existing mechanism works) |
| 5 — os_tool_executions.py split | Deferred (1 day short of stability condition) |
