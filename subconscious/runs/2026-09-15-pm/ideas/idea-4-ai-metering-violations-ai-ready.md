# Idea 4 — Promote GH #871 AI Metering Violations to ai-ready Issues

**Category:** code_health / security
**Effort:** S (create 3-5 scoped issues from the systemic summary)
**Confidence:** MEDIUM
**Status:** WEAKENED (issue-to-pr loop status unverified)

---

## Problem

Step 9L filed GH #871 today as a systemic summary covering 20 router violations and 24 service violations (44 total). Summary issues aren't actionable for the issue-to-pr loop, which requires:
1. Issues labeled `ai-ready`
2. Small, independently implementable scopes

GH #871 is too large to implement as one PR. The loop won't pick it up.

Step 9D reports: **0 ai-ready issues open** — a major state change from the 30-40 stalled issues of prior months.

---

## Proposed Action

Create 3-5 scoped `ai-ready` issues from GH #871's findings, each covering one router file or one small cluster of related violations. Example:

- "Add ai_usage_guard to backend/routers/leads.py mutating endpoints" (5 specific routes)
- "Add ai_usage_guard to backend/routers/conversations.py" (3 routes)
- "Add ai_usage_guard to backend/routers/appointments.py" (2 routes)

Each issue would be:
- Labeled: `ai-ready`, `billing`, `tech-debt`
- Scoped to ≤200 LOC change
- Has acceptance criteria (specific function signatures + guard pattern)
- Independently implementable

---

## Why WEAKENED

1. **Issue-to-pr loop status unverified**: Step 9D shows 0 ai-ready issues but the loop itself may not be running (check GH #399 — was the autonomous engineering loop ever verified running after GH #500 dark Actions?).

2. **Sequencing**: Filing ai-ready issues is only valuable if the loop actually processes them. Filing 5 issues that never get processed just adds backlog noise.

3. **Scoping complexity**: Each metering violation may have different fix patterns (some need budget checks, some need token-count calls). The sub-issue scoping itself requires reading the violations carefully to avoid misleading acceptance criteria.

---

## Recommendation

Run 122: verify issue-to-pr loop is operational first. If running, elevate this to winner.
