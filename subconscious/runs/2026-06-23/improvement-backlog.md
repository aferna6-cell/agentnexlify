# Improvement Backlog — 2026-06-23

## Active
- **Check 7: Plan-name gate coverage** — Add ~10-line block to `check_project_invariants.py`: import `CURRENT_PAID_PLANS` from `plan_catalog`; verify `sms_rate_limiter._UNLIMITED_PLANS`, `api_key_auth._ALLOWED_PLANS`, and `billing_reconciliation` cap dicts each contain all current plans; FAIL on missing. (AUTONOMOUS-EXECUTABLE — nightly-commit-review can execute tonight)

## Parking Lot (survived debate but not chosen)

- **PR #209 timing-safe token comparison** (Bonus Action — investigate then merge or close): `check_project_invariants` Check 12 (run 52 winner) added a pre-commit WARNING for `===` on X-Agent-Token but did not fix the live code. PR #209 may patch `agent-service/src/auth.ts` to use `timingSafeEqual`. Review the diff — if it genuinely fixes the vulnerable line, merge before stale-draft cleanup closes it. If it's scaffolding only, close with a note.

- **AI-to-Human Handoff v1** (68 days, first priority after quick wins): Oldest open customer_value item. All 7 industry simulations impacted. `os_outbound_mirror.py` (PR #188, 152 tests) provides the delivery layer. Action: detect trigger phrases ("talk to someone", "speak to a person", "human help") in `widget_chat.py`; set `lead.status = "needs_follow_up"`; call `os_outbound_mirror.send_sms(owner_phone, ...)` with email fallback. Run 38 scoped this to ~1 day. Now unblocked — both mandate items (GH #292/#293, GH #308) resolved.

- **Merge Batch A+D dependency PRs** (11 PRs: #342, #281, #279, #277, #340, #273, #15, #14, #13, #12, #11): Batch A = 6 dev-dep patches (vitest, @typescript-eslint, @playwright); Batch D = 5 GitHub Actions bumps. Classified MERGE-SAFE in 2026-06-22 PR audit once CI green. PR #348 (CI minute budget) merged — CI now green. Clears 11+ stale PRs in one pass.

- **Deterministic migration object-existence audit** (`scripts/check_migration_objects.py`): GH #263 ("24 pending migrations") confirmed false positive — numeric diff unreliable. Parse DDL targets (CREATE TABLE, ADD COLUMN, CREATE INDEX, CREATE FUNCTION) from each `migrations/NNN_*.sql`, query `information_schema` for existence, output: confirmed-missing vs applied-under-different-name vs truly-pending. Eliminates recurring false-alarm class.

## Rejected This Run
- None killed outright. Ideas 2 (PR #209) and 3 (AI-to-Human Handoff) were WEAKENED by the debate — PR #209 on uncertain evidence, AI-to-Human on activation energy mismatch — but both survive to parking lot.

## Questions for Next Run
- Has Check 7 been implemented by nightly-commit-review? Run `python3 scripts/check_project_invariants.py` and confirm it includes Check 7 output and exits 0 on a clean codebase.
- PR #209: reviewed and merged or closed? Timing attack window on X-Agent-Token is live until one of these happens.
- AI-to-Human Handoff: 68 days is the oldest open item. Now that both mandate bugs are resolved, what is the actual blocking constraint on this feature?
