# Debate Log — Run 121 (2026-09-12)

Top 3 ideas: 1 (Step 9G MCP fix), 4 (SUPABASE_ACCESS_TOKEN unknown-date issue), 3 (os_tool_executions.py god-class monitor)

---

## Idea 1: Fix Step 9G — Replace gh CLI with `mcp__github__actions_run_trigger`

### Challenge
- Is the evidence strong enough? KB is 17d stale — this is real but might have other causes. Did Step 9G fail silently every nightly?
- Is `mcp__github__actions_run_trigger` actually available in CCR sessions? Tool list shows it as a deferred tool but that doesn't prove it works.
- Step 9G was already "implemented" in run 101 using gh CLI. Fixing the implementation method is effectively reimplementing the same idea — does that count as a new direction?
- What if the KB is stale for reasons OTHER than Step 9G failing (e.g. ANTHROPIC_API_KEY expiry, workflow permissions)?

### Defend
- Evidence is strong: SKILL.md line 323 explicitly uses `gh workflow run` — grep confirms. `gh` is not installed in cloud CCR sessions (confirmed in summary: "gh CLI unavailable in cloud CCR sessions"). Causal chain is clear.
- `mcp__github__actions_run_trigger` is listed in the available MCP tools (system-reminder). Tool schema needs ToolSearch to load but availability is confirmed. CCR sessions have MCP access by design.
- This IS a new direction from run 101: run 101 implemented Step 9G using the wrong tool (gh CLI); this run proposes fixing the tooling. Precedent: Step 9J was also a "fix" to an already-implemented step (Dependabot rebase trigger) and was accepted as a valid winner in run 112.
- Even if KB staleness has additional causes, fixing Step 9G removes one confirmed blocker. Other causes can be addressed in subsequent runs.

### Verdict: **SURVIVES**
Causal chain is tight. Run 120 mandate explicitly requests evaluation. Implementation is XS effort (single block edit). High leverage: restores KB health which feeds nightly KB-first rule.

---

## Idea 4: SUPABASE_ACCESS_TOKEN rotation GH issue

### Challenge
- Filing a GH issue from the subconscious run directly is outside normal scope (subconscious recommends; nightly acts). This mixes recommendation with action.
- The alternative interpretation — mandate Step 9E to handle unknown-date credentials — is a SKILL.md change, same category as Idea 1 but for a different problem. Are both needed this run?
- SUPABASE_ACCESS_TOKEN may actually be expired already (unknown date = could be years old or months old). Filing a GH issue doesn't fix the problem.
- Is this lower leverage than Idea 1? Idea 1 restores a broken automated system; Idea 4 alerts about a manual action needed. Automated fixes > manual alerts.

### Defend
- SUPABASE_ACCESS_TOKEN is required by kb-autopopulate.yml. If expired, even a fixed Step 9G won't restore KB health. The two are linked.
- However: the subconscious should NOT directly file GH issues (no MCP calls in artifacts phase). The recommendation should be to extend Step 9E to handle unknown-date credentials.
- This is a valid XS SKILL.md edit: in Step 9E, when `last_rotated = "unknown"`, always fire an issue (don't wait for days_remaining threshold). Evidence: one credential already in this state.

### Verdict: **WEAKENED → PARKING LOT**
Valid concern but narrower than Idea 1. If Step 9G is fixed and KB is restored, SUPABASE_ACCESS_TOKEN becomes more critical (any expiry there would break a fixed 9G). But Idea 1 has higher immediate leverage. Park this as Step 9E unknown-date handling for run 122.

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
- The monitor is literally `wc -l` — it's not a new test suite, just an arithmetic check. Runtime cost is ~0ms.

### Verdict: **WEAKENED — deferred**
Evidence for immediate risk is insufficient (436L with non-linear commit cadence). Valid concern but lower urgency than Idea 1. Park for run 122 if file hits 480L+.

---

## Summary

| Idea | Verdict | Outcome |
|------|---------|---------|
| 1: Fix Step 9G (gh CLI → MCP) | SURVIVES | **WINNER** |
| 4: SUPABASE_ACCESS_TOKEN unknown-date | WEAKENED | Parking lot |
| 3: Step 9M god-class monitor | WEAKENED | Parking lot |
| 2: Governance entry for Step 9E | Not debated (administrative) | Implement as part of Phase 6 housekeeping |
| 5: Step 9N countdown log | Not debated | Parking lot (low urgency) |
