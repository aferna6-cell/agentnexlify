# Idea 5: customer-gaps.md Stale Entry Cleanup

**Category:** workflow / doc  
**Effort:** XS  
**AUTONOMOUS-EXECUTABLE:** YES

## Evidence

`docs/dev-knowledge/customer-gaps.md` lists "Lead source analytics | All | Source column exists, no dashboard visualization | Low" as an **open gap**. But run 2 (2026-04-06) implemented this — AnalyticsPage.jsx has `fetchLeadSources` + BarChart with per-source colors, confirmed in run 9 governance correction (2026-04-27).

Stale gap entries cause future agents (or subconscious runs) to recommend already-done work, wasting cycles.

## Action

Move "Lead source analytics" from the "Open Gaps — Cross-Industry" table to the "Resolved Gaps" table in `docs/dev-knowledge/customer-gaps.md`. Add row:
```
| Lead source analytics     | All   | Cycle 2 (run 2, AnalyticsPage.jsx BarChart by source) |
```

## Expected Impact

- Prevents future agents from recommending already-implemented work
- Accurate gap list = better signal for future runs

## Why Not Winner

XS doc cleanup with no revenue or code health impact. But should run as a bonus action alongside the winner.
