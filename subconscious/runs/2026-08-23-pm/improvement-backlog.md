# Improvement Backlog — 2026-08-23-pm (Run #109)

## Active (implemented this run)

### Step 9J — Dependabot Auto-Merge with Major-Version Safety Gate
- **Implemented:** 2026-08-23-pm (autonomous-executable, 1st carry-forward mandate)
- **Location:** `.claude/skills/nightly-commit-review/SKILL.md` after Step 9I
- **Effect:** Merges CI-green patch/minor Dependabot PRs nightly. Skips: major version bumps, non-clean CI, review requests, blocking labels.

---

## Parking Lot (next runs — evidence gathered, not yet mandate-threshold)

### Step 9K — Stale Subconscious PR Closer
- **Evidence:** 6 open subconscious draft PRs (oldest #606: 26 days). Run 109 mandate named Step 9K candidate at ≥3 PRs — threshold exceeded.
- **Proposal:** Add nightly block to close subconscious PRs older than 14 days with 0 code commits. Add closing comment explaining automated closure.
- **Status:** 1st mandate mention (run 109). Will become autonomous-executable at run 110 carry-forward if not approved before.
- **Target run:** 110

### KB Autopopulate Self-Healing Enhancement
- **Evidence:** KB 31 days stale (last run: 2026-07-23). GH #403 has Steps 9F/9G already wired. Root cause: ANTHROPIC_API_KEY + SUPABASE secrets missing from GH Actions.
- **Proposal:** Add Step 9H variant that also checks SUPABASE_URL + SUPABASE_ANON_KEY status (not just ANTHROPIC_API_KEY). Currently 9F/9G only comment on GH #403 — staleness continues.
- **Status:** Blocked by GH #399 (AUTOPILOT_GH_TOKEN) and GH #403 (secrets). Human action required first.
- **Target run:** Post-GH #399 resolution

---

## Rejected Paths (do not revisit)

### Middleware-level block_demo_role guard (autonomous)
- **Rejected:** Wrong channel. M-effort architectural change. Subconscious handles SKILL.md edits, not 97-file router changes or core auth refactors.
- **Correct channel:** Human-approval engineering session + issue-to-pr-loop (blocked by GH #399).

### Semver-aware Dependabot PR labeler (Step 9L)
- **Rejected:** Over-engineers Step 9J. Title-regex major-version check in 9J is simpler and sufficient. Labeler adds complexity without enough gain for current inventory.

---

## Open Blockers (human action required — not autonomous-executable)

| Issue | Description | Day count | Action needed |
|-------|-------------|-----------|---------------|
| GH #399 | AUTOPILOT_GH_TOKEN expired — 30 ai-ready issues blocked, issue-to-pr-loop dark | Day 41+ | Human: rotate token in Railway env vars |
| GH #403 | KB autopopulate 31 days stale — ANTHROPIC_API_KEY + SUPABASE_URL + SUPABASE_ANON_KEY missing from GH Actions | Day 29+ | Human: add all 3 secrets to GH Actions |
| GH #669 | 97/97 routers missing Depends(block_demo_role) — demo tenants can mutate data | Filed 2026-08-20 | Human: approve architectural approach (middleware vs per-router Depends) |

---

## Open Questions

1. **Step 9J — mergeable_state field reliability:** Does `mcp__github__pull_request_read` return `mergeable_state: "clean"` consistently across all PR types, or does it sometimes return `null` for PRs that haven't been evaluated yet? If null, should Step 9J skip or re-check after delay?
2. **Step 9K timing:** Should Step 9K close PRs that are open but have active comments? The 0-code-commits filter should cover this (subconscious PRs with active engagement would have code commits), but edge cases possible.
3. **Dependabot PR title format stability:** Confirmed format is "Bump {package} from {old} to {new}" — but is this stable across all package ecosystems (npm, pip, GH Actions)? The major-version regex needs to work for all three.
