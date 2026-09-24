# Winning Concept — 2026-09-24 (Run 128)

**Winner:** Step 9J Priority Queue — sort:created-asc + perPage=5
**Category:** workflow_efficiency
**Carry count:** 1 (fresh direction; run 127 winner resolved by nightly-2026-09-24)
**Status:** Recommend (autonomous-executable via SKILL.md channel)

---

## Recommendation

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9J.1: change the `search_pull_requests` call to add `sort: "created"`, `direction: "asc"` (oldest first), and `perPage: 5`. This retrieves only the 5 oldest Dependabot PRs per run, ensuring the highest-CVE-age PRs are always processed within the token budget.

---

## Why This, Why Now

7+ consecutive nightly runs show 17/19 Dependabot PRs skipped per run. Token budget depletes before Step 9J processes all results. The current search uses default ordering (likely insertion/recency), meaning older PRs with higher CVE-age risk may never be processed while newer PRs accumulate.

With `sort:created-asc`, the 5 oldest open Dependabot PRs are retrieved first. Any PR that passes CI + is Dependabot-authored gets merged or rebase-triggered. Next run picks up the next 5 oldest. Security patches land within 1-2 nightly cycles instead of multi-week delays.

Run 127 winner (Step 9E P0 tier) was just implemented by nightly-2026-09-24, clearing the carry-forward queue. Run 128 picks Step 9J as the next highest-leverage workflow gap.

---

## Implementation Sketch

In `.claude/skills/nightly-commit-review/SKILL.md`, Step 9J block, locate the `search_pull_requests` call at Step 9J.1. Change the parameters:

```
Current:
  search_pull_requests(query: "is:open author:app/dependabot repo:aferna6-cell/agentnexlify")

After fix:
  search_pull_requests(
    query: "is:open author:app/dependabot repo:aferna6-cell/agentnexlify",
    sort: "created",
    direction: "asc",
    perPage: 5
  )
```

Also update the Step 9J log entry format to include sort confirmation:
```
"Step 9J: {N} oldest Dependabot PRs checked (sort:created-asc), {M} merged, {R} rebase-triggered, {K} skipped."
```

Total change: ~3 lines modified in existing Step 9J.1 block. No new files, no migrations, no code changes.

---

## What This Resolves

Persistent evidence pattern across runs 121–128: 17/19 Dependabot PRs skipped every nightly run. No individual PR fix addressed the root cause (token budget ordering). This change makes the budget-constrained behavior deterministic and security-prioritized rather than arbitrary.

---

## Confidence

**HIGH** — Evidence is direct (7+ consecutive runs, same symptom), action is atomic (3-line SKILL.md edit), blast radius zero (sort/limit affects which PRs are retrieved, not how they're processed), mechanism identical to Steps 9F/9G/9I/9J/9K/9L (all SKILL.md edits, all working). Debate verdict: SURVIVES.

---

## Run 128 Mandate

1. Verify Step 9J search call has `sort: "created"`, `direction: "asc"`, `perPage: 5` after nightly implements.
2. First nightly with fix: log entry confirms "oldest Dependabot PRs checked (sort:created-asc)". How many merged? How many rebase-triggered?
3. **CRITICAL:** AUTOPILOT_GH_TOKEN expires 2026-10-02 (8 days). GH #399 open. Step 9E P0 firing daily. Human action required.
4. KB staleness (29 days): Step 9G fires via MCP but ANTHROPIC_API_KEY (#403) + VOYAGE_API_KEY (#618) block compile. Track whether GH #403 sees movement.
5. GH #881 (os_tool_executions.py split): spec sufficient for loop execution when GH #399 resolves?

---

## Escalation Status

First carry. Autonomous-executable from run 128 via SKILL.md channel (same as Steps 9F/9G/9I/9J/9K/9L). Implementation when nightly next fires: direct SKILL.md edit per this sketch.

**AUTOPILOT_GH_TOKEN expires 2026-10-02. Human action required. See GH #399.**
