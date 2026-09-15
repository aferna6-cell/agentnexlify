# Idea 5 — Step 9J Major Version PR Escalation: File GH Issues for Deferred PRs

**Category:** workflow_efficiency / operational
**Effort:** XS (add GH issue creation to Step 9J skipped-major block)
**Confidence:** LOW-MEDIUM
**Status:** KILLED

---

## Problem

Step 9J skips major version Dependabot PRs with a log entry. Today's nightly skipped 4 major version PRs:
- #863 react-dom 18→19 in /demo-platform
- #861 react 18→19 in /demo-platform
- #860 react 18→19 in /frontend
- #859 vitest 4→5 in /frontend

These accumulate silently. No GH issue, no assignee, no audit trail.

---

## Why KILLED

Upon investigation, the issue is lower-priority than it appears:

1. **Step 9J already logs correctly**: The nightly review file captures all skipped PRs with justification. The human can read the nightly review.

2. **The PRs themselves ARE the tracking mechanism**: Dependabot PRs stay open indefinitely. They're already filed and visible. Filing a GH issue would be duplicate tracking.

3. **React 18→19 migration is a deliberate multi-week effort**: Creating an issue doesn't help. What's needed is a migration plan, not an issue. The GH issue would be "WONTFIX within the quarter" immediately.

4. **Low incremental value**: The marginal improvement over current logging is minimal. Human needs to decide when to tackle major version bumps — an issue doesn't change that calculus.

---

## Verdict

KILLED. Step 9J behavior is correct. Logging skipped PRs in the nightly review file is sufficient. No implementation needed.
