# Winning Concept — Run 2026-09-24-pm (Run 129)

## Title
Step 9J Priority Queue — sort:created-asc + perPage=5 (2nd carry-forward)

## Category
workflow_efficiency

## Effort
XS (2-parameter addition, 1 function call, ~3 lines in SKILL.md)

## Problem
Step 9J in nightly-commit-review SKILL.md calls `search_pull_requests` to find eligible Dependabot PRs. Default sort is newest-first. Token budget depletes before all PRs are processed, leaving 12-14 PRs unprocessed per run. The oldest PRs (#885-#891) carry the highest CVE-age risk and are systematically processed last or skipped.

## Mechanism
Add `sort: 'created', direction: 'asc', perPage: 5` to the `search_pull_requests` call in Step 9J.1. This ensures:
1. Oldest (highest CVE-age risk) Dependabot PRs are processed first within the token budget window
2. Each run processes ~5 PRs deterministically instead of random selection
3. PRs are processed in FIFO order — oldest CVEs resolved first

## Exact Change
In `.claude/skills/nightly-commit-review/SKILL.md`, Step 9J.1 `search_pull_requests` call:

**Add parameters:**
```
sort: 'created',
direction: 'asc',
perPage: 5
```

**Update log line to include:** `"sort:created-asc"`

## Evidence
- 7+ consecutive nightlies show 17/19 Dependabot PRs skipped due to token budget depletion
- Oldest PRs #885-#891 carry highest CVE-age risk
- grep=0 in current SKILL.md confirms fix not yet applied
- Run 128 active_direction set to this idea — 1st carry-forward now eligible for autonomous-executable channel

## Autonomous-Executable Status
**ELIGIBLE** — this is a SKILL.md edit with XS risk. nightly-commit-review autonomous-executable channel applies. No human approval required per governance (1st carry-forward = nightly can implement this run cycle).

## Expected Impact
- Oldest 5 Dependabot PRs processed per run (deterministic FIFO)
- CVE-age risk reduced: PRs #885-#891 processed before newer ones
- No change to total PRs processed per run (token budget unchanged)
- Log output gains "sort:created-asc" label for audit clarity

## NOT implementing this run
This is a recommendation only. Implementation via nightly-commit-review autonomous-executable channel on next nightly cycle.
