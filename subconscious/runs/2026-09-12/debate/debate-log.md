# Debate Log — Run 121 (2026-09-12)

Top 3 ideas: 1 (Step 9G MCP fix), 4 (SUPABASE_ACCESS_TOKEN unknown-date issue), 3 (os_tool_executions.py god-class monitor)

---

## Idea 1: Fix Step 9G — replace gh CLI only after verifying a GitHub Actions MCP path

### Challenge
- Is the evidence strong enough? KB is 17d stale — this is real but might have other causes. Did Step 9G fail silently every nightly?
- Are the proposed GitHub Actions MCP trigger/list capabilities actually available in the **nightly CCR execution surface**? Seeing a candidate tool name elsewhere is not end-to-end proof.
- Step 9G was already "implemented" in run 101 using gh CLI. Fixing the implementation method is effectively reimplementing the same idea — does that count as a new direction?
- What if the KB is stale for reasons OTHER than Step 9G failing (for example missing `ANTHROPIC_API_KEY`, workflow permissions, or another workflow-level failure)?

### Defend
- Evidence is strong that the **current mechanism is invalid**: SKILL.md uses `gh workflow run`, while gh CLI is unavailable in the cloud nightly environment. That proves the existing Step 9G trigger path needs replacement.
- A GitHub Actions MCP trigger/list path is a plausible replacement, but availability and exact schemas must be verified in the actual nightly CCR session before implementation. No artifact should call the candidate MCP actions confirmed until that end-to-end proof exists.
- This IS a new direction from run 101: run 101 implemented Step 9G using a mechanism that cannot execute in the target environment; this run recommends a verification-gated replacement mechanism.
- Even if KB staleness has additional causes, replacing the invalid trigger mechanism removes one blocker. GH #403 remains a separate workflow-execution prerequisite and must not be represented as solved by trigger migration.

### Verdict: **SURVIVES, VERIFICATION-GATED**
The need to replace `gh` is well supported. The specific MCP implementation is not yet proven. Winner status means "verify capability, then implement only if proven," not "MCP availability confirmed."

---

## Idea 4: SUPABASE_ACCESS_TOKEN rotation GH issue

### Challenge
- Filing a GH issue from the subconscious run directly is outside normal scope (subconscious recommends; nightly acts). This mixes recommendation with action.
- The alternative interpretation — extend Step 9E to handle unknown-date credentials — depends on a Step 9E escalation implementation that is itself still pending.
- SUPABASE_ACCESS_TOKEN may already have an existing ops/human-action tracker under a broader title. Filing a new issue without credential-identity dedup could create duplicate operational work.
- Filing an issue does not itself rotate or verify the credential.

### Defend
- Unknown rotation date is still a real observability gap: age-based logic cannot calculate a warning or due date when `last_rotated` is unknown.
- The safer contract is to route this through the pending Step 9E implementation using credential-identity dedup, reuse an existing tracker when present, and request verification of the actual rotation date.
- That keeps recommendation and execution boundaries clean while preserving the signal.

### Verdict: **WEAKENED → PARKING LOT**
Valid concern, but it should be incorporated into the actual Step 9E implementation rather than create an un-deduplicated issue from this run. Park as unknown-date handling for the Step 9E lane.

---

## Idea 3: Step 9M — os_tool_executions.py god-class early warning

### Challenge
- Is this premature? File is at 436L, 164L below the 600L threshold. Current growth rate is ~25L per commit but commits are sporadic (2 in 3 days after several weeks of stability).
- Adding Step 9M creates monitoring overhead for a file that isn't a problem yet. Rule 11 (additive wins) applies but this is adding a new nightly step rather than a quick fix in a file already touched.
- Is the evidence pattern reliable? Two commits in 3 days is a spike, not a trend. The file was stable for much of its history.
- There are likely many files approaching 600L in the codebase — why monitor just this one?

### Defend
- os_tool_executions.py is the Agent OS tool router — it handles ALL tool execution in the product. When it becomes a god-class, the refactor blast radius is enormous (many callers). Early warning at 500L gives 3+ commit window before threshold.
- Two commits in 3 days adding Gmail failure handling AND email approval surface signal a pattern: Agent OS is expanding to handle more edge cases. This is a directional signal, not a one-time spike.
- The monitor is literally `wc -l` — it's not a new test suite, just an arithmetic check. Runtime cost is negligible.

### Verdict: **WEAKENED — deferred**
Evidence for immediate risk is insufficient (436L with non-linear commit cadence). Valid concern but lower urgency than Idea 1. Park for run 122 if file hits 480L+.

---

## Summary

| Idea | Verdict | Outcome |
|------|---------|---------|
| 1: Fix Step 9G (`gh` → verified MCP path) | SURVIVES, verification-gated | **WINNER** |
| 4: SUPABASE_ACCESS_TOKEN unknown-date | WEAKENED | Parking lot / Step 9E contract |
| 3: Step 9M god-class monitor | WEAKENED | Parking lot |
| 2: Step 9E governance status | Administrative correction | Keep pending until implementation exists |
| 5: Step 9N countdown log | Not debated | Parking lot (low urgency) |
