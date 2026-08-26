# Improvement Backlog — Run 110 (2026-08-26-pm)

## Active
- **Fix Step 9J check-runs gate**: edit `.claude/skills/nightly-commit-review/SKILL.md` to gate Dependabot merges on commit check-run conclusions (all `completed` + `success`) instead of `mergeable_state: "clean"`. Human approves, nightly implements.

## Parking Lot (survived debate but not chosen)
- **block_demo_role FastAPI middleware** (GH #669): add middleware to `backend/main.py` intercepting POST/PUT/DELETE/PATCH, checking block_demo_role unless path in allowlist. M-effort. Run 111 candidate when GH #399 unblocks issue-to-pr-loop.
- **Step 9K stale subconscious PR report**: add Step 9K to nightly SKILL.md — list open `subconscious/*` PRs >7 days old, log, post comment. Report-only. S effort. Run 111 candidate alongside Step 9J fix (both are SKILL.md edits).
- **Voice addon double-billing fix** (GH #687): enhance GH #687 with implementation sketch — detect and cancel active voice addon Stripe subscription when upgrading to `agent_os`. M-effort billing path, human approval.
- **churn_watch.py daily trigger**: wire `churn_watch.py` as morning-digest step to surface top-3 at-risk tenants daily. Requires verifying endpoint/CLI path first.

## Rejected This Run
- None killed outright — all 5 ideas showed evidence of real problems. Top 3 debated; winner chosen by impact × autonomy.

## Questions for Next Run
1. Did Step 9J fix produce merges? Or did check-run query surface a new issue (no CI on PRs)?
2. GH #399 resolved? If yes, issue-to-pr-loop unblocks 30+ ai-ready issues including #687 (double-billing) and #669 (middleware).
3. churn_watch.py: is there an HTTP endpoint or only a CLI script? What's the invocation path?
4. Step 9K: how many open subconscious PRs exist? At ≥3, make Step 9K run 111 winner.
