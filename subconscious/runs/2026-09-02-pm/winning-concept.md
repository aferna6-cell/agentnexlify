# Winning Concept — Run 115 (2026-09-02-pm)

## Recommendation
Add a "PRs found: N" diagnostic log line to Step 9J in `.claude/skills/nightly-commit-review/SKILL.md` — before the skip decision — so nightly logs definitively show whether Step 9J is correctly skipping (0 PRs found) or experiencing a detection failure (N > 0, skip is wrong).

## Why This, Why Now
Run 115 mandate item 3 flagged Step 9J as open: nightly-2026-09-01 fired (rebased PRs #721 and #722) but nightly-2026-09-02 shows "9J Dependabot: skipped" with zero diagnostic context. Three nightly logs have now shown this ambiguity and the bug-patterns.md "silent-green automation" pattern (Keys Koffee: widget missing 5+ weeks, nobody noticed) applies directly — a step that says "skipped" is indistinguishable from "correctly skipped" vs "detection failed". A 3-line SKILL.md edit adding "Step 9J: N Dependabot PRs found via search_pull_requests" before the skip decision makes the nightly self-diagnosing.

## Implementation Sketch
1. Open `.claude/skills/nightly-commit-review/SKILL.md`.
2. Locate Step 9J block (the `search_pull_requests` block added run 112).
3. In Step 9J.2 (after the `search_pull_requests` call), add a mandatory log line BEFORE the "if count == 0: skip" check:
   - `Log: "Step 9J: {len(prs)} Dependabot PRs found via search_pull_requests"`
4. This means: whether 0 or N PRs are found, the nightly report always contains "Step 9J: N Dependabot PRs found via search_pull_requests" — making the skip or action self-evident.
5. Commit: `feat(nightly): add Step 9J diagnostic PR count log before skip decision`

**Exact insertion point:** After the `mcp__github__search_pull_requests` call in Step 9J, before the `if len(results) == 0: skip` branch.

**Log line to add:**
```
Log to nightly report: "Step 9J: {len(results)} Dependabot PRs found via search_pull_requests"
```

## What This Replaces
Active direction: run 114 winner (Step 9K stale subconscious PR audit — IMPLEMENTED). Step 9K is now in SKILL.md and confirmed firing. This run opens a new direction: Step 9J diagnostic transparency.

## Confidence
**HIGH** — evidence is unambiguous (3 nightly logs with same diagnostic gap); silent-green automation pattern from bug-patterns.md is directly applicable; ~3-line SKILL.md edit; same autonomous-executable channel as Steps 9C/9E/9F/9G/9I/9J/9K; zero production code changes; zero architectural risk.

## Run 116 Mandate
1. Did nightly-2026-09-03 show "Step 9J: N Dependabot PRs found"? If N=0, skip confirmed correct. If N>0 and still skipped, detection bug.
2. os_tool_executions.py stability check: 0 commits since 2026-09-02? If yes → run 116 god class split candidate.
3. GH #684 SUPABASE_ACCESS_TOKEN: still unset in Railway?
4. M9.2 persistence engine: schema migration filed (migrations/NNN_m9_workflow_state.sql)?
5. Step 9L widget health mechanism: any update on Supabase MCP headless availability?
6. Stale subconscious PRs: count and ages — approaching escalation threshold (≥5 or any >60d)?
