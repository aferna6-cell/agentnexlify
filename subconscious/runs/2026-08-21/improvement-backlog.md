# Improvement Backlog — 2026-08-21

## Active
- Step 9J (Dependabot auto-merge) — block added to nightly SKILL.md this run; mandate condition met and executed directly (run 109, 1st carry-forward)

## Parking Lot (survived debate but not chosen)

### GH #669 — Middleware-level block_demo_role fix (Bonus Action — post comment this run)
- **Evidence:** Step 9I first execution (2026-08-20) swept 97/97 backend routers — ALL missing `Depends(block_demo_role)`. Per-endpoint patching is O(n) forever. Middleware fix protects current + future endpoints in one change.
- **Why parked:** M-effort, requires human architectural decision (middleware vs per-router). Subconscious cannot execute autonomously. GH #669 already tracks the finding. Bonus action: post middleware proposal comment to frame the choice.
- **Next:** human reviews GH #669, decides approach, closes the class.

### Step 9K — Stale subconscious PR closer (Run 110 candidate)
- **Evidence:** 5+ draft subconscious PRs open (#626, #613, #611, #606, #575 plus newer). Each nightly run adds another. PR board noise hides real review needs.
- **Why parked:** Two SKILL.md changes in one run (9J + 9K) increases partial-implementation risk. Step 9J has mandate priority. Step 9K evidence is valid but not mandate-triggered.
- **Proposed block:** List open PRs with head starting "subconscious"; if age >30 days AND no review activity → close with "superseded by run N" message.
- **Next:** Run 110 — propose Step 9K as winner if no higher-priority mandate fires.

## Rejected This Run
- **Idea 4 (bug-patterns.md block_demo_role entry):** GH #669 already documents the finding; bug-patterns.md entry would be redundant, not new signal. Killed in favor of Step 9J.
- **Idea 5 (GH #403 full secrets audit comment):** Run 108 bonus already posted SUPABASE_URL + SUPABASE_ANON_KEY diagnostic. Third comment without new information has diminishing signal. Killed.

## Questions for Next Run
- Did Step 9J execute? Check nightly-2026-08-22 log — did it merge any Dependabot PRs?
- Did GH #669 receive a human response? Middleware vs per-router decision pending.
- Is Step 9K the right next Step? Or has a new mandate-trigger finding emerged?
- GH #399 (AUTOPILOT_GH_TOKEN Day 40+): any human action? 30 ai-ready issues still blocked.
