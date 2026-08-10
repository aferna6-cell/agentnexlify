# Improvement Backlog — Post Run 107

## Implemented this run
- [x] Step 9H: KB Autopopulate Outcome Monitor — `.claude/skills/nightly-commit-review/SKILL.md` (after Step 9G)
- [x] Step 1.5: Detached HEAD Guard — `.claude/skills/nightly-commit-review/SKILL.md` (before Step 2)

## Recommended (next cycles)

### P1 — Step 9F/9G Staleness Compliance (3 consecutive misses)
**What:** Move Step 9F (KB staleness check) to the beginning of the Scheduled Task Prompt (after git pull, before commit review). Currently Steps 9F/9G appear late in the skill and are being skipped when nightly sessions end early.
**Evidence:** 2026-08-08, 2026-08-09, 2026-08-10 nightlies all omitted Steps 9F/9G despite KB being 16-18d stale.
**Risk:** MEDIUM (SKILL.md reorder). Worth a dedicated implementation cycle.
**Carry-forward:** cycle 1

### P2 — Step 9H (Idempotent PR Pile Alerter) — run 106 carry-forward
**What:** Once-per-7-days alert when >3 open subconscious draft PRs exist.
**Evidence:** Currently 1 open PR (PR #626). Alerter would not trigger. Low urgency.
**Risk:** LOW.
**Carry-forward:** cycle 2 (run 106 = cycle 1, this run = cycle 2)

### P3 — GH #500 Actions Billing Diagnostic
**What:** Comment on GH #500 clarifying that billing limit is NOT the blocker (GH Actions runs queue and complete). Root cause is `continue-on-error: true` masking missing secrets. Step 9H now surfaces this on next stale KB cycle — so #500 diagnostic may become redundant.
**Risk:** LOW.
**Carry-forward:** cycle 1

### P4 — client_id sentinel to tenant_api_keys
**What:** Test assertion that no code queries `tenant_api_keys` using `tenant_id`. Run 107 mandate included this but evidence from connector_awareness.py shows `tenant_id` parameter is intentionally passed alongside `client_id` for routing. Needs deeper audit before asserting violation.
**Risk:** MEDIUM investigation.
**Carry-forward:** cycle 1

## Resolved this session
- GH #640: block_demo_role guard on POST /buy-usage — resolved 2026-08-08, confirmed 2026-08-09
- Detached HEAD incident (2026-08-07) — root cause in SKILL.md now addressed
- False-success KB monitor gap — Step 9H now in SKILL.md
