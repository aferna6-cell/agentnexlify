# Idea 4 — React 18→19 Upgrade Readiness Checklist

**Category:** code_health / dependency_management
**Effort:** M (research + checklist doc, no code changes)
**Confidence:** MEDIUM

## Problem

5 Dependabot PRs blocked as major version bumps requiring human review:
- #863 react-dom 18→19 in /demo-platform
- #861 react 18→19 in /demo-platform
- #860 react 18→19 in /frontend
- #859 vitest 4→5 in /frontend
- #864 mcp >=2.2.0,<3 (major — CI unstable)

These have been blocked for 5+ nightly reviews. No progress. Human reviewer
cannot act without a migration checklist.

Evidence (2026-09-17.md):
- Step 9J: 5 PRs open, 0 merged, 5 skipped (same as yesterday)
- All 4 React 18→19 PRs blocked "major version — human review required"

## Implementation

Create `docs/dev-knowledge/react-19-migration-checklist.md`:
1. Breaking changes inventory (React 19 release notes → list our specific usage)
2. Check `frontend/src/` for deprecated patterns (useLayoutEffect server, string refs, findDOMNode)
3. Check `demo-platform/` for same
4. vitest 4→5 breaking changes relevant to our test suite
5. Go/no-go recommendation per package + risk rating

This is a recommendation doc only. Human decides merge order.

## Expected outcome

- Human reviewer has concrete checklist → unblocks 4 React PRs
- Vitest upgrade assessed separately (test suite impact)
- mcp major version deferred (CI unstable — independent issue)
- Backlog of 5 blocked PRs reduced to 1 (mcp only)

## Risk

LOW. Read-only evidence gathering. No production code changes.
Research effort ~1 hour of subconscious time.

## Comparison to other ideas

Lower urgency than Step 9E (AUTOPILOT_GH_TOKEN expires in 15 days) and
Step 9G (KB 22d stale, fix is 1 line). Valuable but not time-critical.
