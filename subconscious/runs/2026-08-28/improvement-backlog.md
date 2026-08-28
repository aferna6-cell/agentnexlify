# Improvement Backlog — Run 110 (2026-08-28)

## Winner (This Run)

| Idea | Verdict | Effort | Status |
|------|---------|--------|--------|
| Fix Step 9J: add `@dependabot rebase` trigger for `unknown` state | **WINNER** | S | Recommendation — autonomous-executable run 111 if not approved |

---

## Parking Lot (Promoted This Run)

### Step 9K: Stale Subconscious PR Closer (report-only)
- **Evidence:** governance.json lists multiple pending_human_action subconscious PRs across runs 90-93. Morning digests flagged stale draft PRs (#575, #606, #611, #613, #625, #626) across multiple runs. PR list noise.
- **Action:** Add Step 9K to nightly SKILL.md — list open PRs with head_branch starting with `subconscious/`, for each open draft >21d with no commits in last 14d, post comment asking human to merge or close. Report-only, no auto-close.
- **Condition:** Promote to winner when ≥3 subconscious PRs confirmed open in nightly check.
- **Note:** run_109_mandate named Step 9K as run 110 candidate — subconscious PR count not verified this run.

### ai-ready Loop Stall Diagnostic (Step 9D+ escalation)
- **Evidence:** 3 ai-ready issues (#643 21d, #660 13d, #669 8d), all stalled with no linked PRs. AUTOPILOT_GH_TOKEN ~55d (OK <76d threshold per Step 9E) but loop appears dead. Root cause unknown.
- **Action:** When oldest ai-ready issue > 14 days with no linked open PR, check if a `loop-stall` GH issue exists (label:loop-stall is:open). If none, file one with stalled issue list + diagnostic checklist + label: loop-stall + human-action-required.
- **Why Parked:** WEAKENED in debate — 5th+ similar diagnostic recommendation; mechanism has been insufficient. If the human hasn't acted on 5 weeks of comments, one more issue may not move the needle. Valid mechanism change (dedicated issue vs count-update comments) but uncertain ROI.
- **Promote when:** Loop stall reaches 30+ days on any ai-ready issue OR human explicitly asks for diagnostic issue.

### Middleware-level `block_demo_role` FastAPI guard (GH #669)
- **Evidence:** 95 routers confirmed missing `block_demo_role`. GH #669 8 days old. 8 days in parking lot (run 108). Closes 95 violations in 1 PR vs 95 individual PRs.
- **Action:** Recommend `DemoRoleGuard` as base APIRouter dependency in `backend/main.py`. Single `Depends(block_demo_role)` on mutating router base class. File GH issue describing architectural approach.
- **Why Parked:** WEAKENED — M-effort, requires human approval, loop stall makes execution uncertain. Technical concern raised: `block_demo_role` is a route-level Depends (needs decoded JWT), not pre-auth middleware. Correct implementation = base APIRouter with dependency, not HTTP middleware.
- **Promote when:** Issue-to-pr-loop resumes (GH #399 resolved) AND human approves architectural approach.

### SUPABASE_ACCESS_TOKEN onboarding checklist (GH #684)
- **Evidence:** Brain connector 36 days stale. Root cause: SUPABASE_ACCESS_TOKEN not in Railway. Step 9C comments add count updates but the exact 3-step checklist (Supabase → Railway → deploy) has never been provided in the issue.
- **Action:** Post targeted comment on GH #684 with 3-step checklist: (1) Supabase dashboard → Project Settings → Access Tokens → Copy, (2) Railway → agentnexlify → Variables → Add SUPABASE_ACCESS_TOKEN, (3) Railway deploy.
- **Why Parked:** Valid bonus action — lower leverage than Step 9J fix. Re-evaluate as bonus action in run 111.
- **Promote when:** Run 111 confirms brain connector still stalled; execute as bonus action (S-effort, 1 comment).

---

## Killed This Run

None killed outright — all non-winner ideas parked with conditions for promotion.

---

## Standing Parking Lot (Carries Forward from Prior Runs)

| Item | Runs in Lot | Promote When |
|------|-------------|--------------|
| Step 9K: stale subconscious PR closer | run 109, 110 | ≥3 subconscious PRs confirmed open |
| Loop stall diagnostic (Step 9D+) | runs 108-110 | 30+ day ai-ready stall OR human request |
| Middleware block_demo_role (GH #669) | runs 108-110 | Loop resumes + human approval |
| SMS Compliance Dashboard | runs 73-110 | Human bandwidth |
| email_sequences N+1 fix | runs 112+... | Email automation adoption grows |
| Cross-tenant isolation test | run 54+ | Next Agent OS sprint |
