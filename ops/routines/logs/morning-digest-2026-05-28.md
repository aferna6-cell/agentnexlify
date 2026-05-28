# Morning Digest — 2026-05-28

**Generated:** 2026-05-28 UTC
**Moratorium:** DAY 24 — Items A/B/D still pending (exit threshold: 2)
**Subconscious:** Run 37 complete — Check 11 NOT yet in pre-commit (nightly review committed summary but skipped implementation)

---

## Commits (last 24h) — 5 total

- `033fc3b` subconscious: run 2026-05-28 — Billing-constant-guard pre-commit Check 11 *(run summary only — CHECK 11 NOT ADDED)*
- `dc5ef8e` ops: nightly-commit-review 2026-05-28
- `301cbcf` feat(os): Agent OS rehaul — Groups A+B+C complete (#188) ← **BIG SHIP**
- `bca2082` test: align mocks with PostgREST `.filter()` chain after `.not_.is_()` cleanup
- `6126397` chore(ai): auto-commit Claude edits (`.not_.is_()` → `.filter()` sweep, 11 files)

**Agent OS rehaul summary (#188):**
- Group A: inbound bridge config UI (backend + frontend)
- Group B: `sms.send` action handler + 7 tests
- Group C: SMS/email/Facebook outbound mirror, RFC 5322 threading, BYO+platform fallback
- Group C phase 3: replay protection via `os_outbound_log` (migration 130, RLS ✓, `client_id` ✓)
- Codebase `.not_.is_()` → `.filter()` migration: 14 production sites, 0 remaining
- Verified: 498 pytest passed, 152 OS tests, frontend build clean

---

## Issues — Active

| # | Title | Status |
|---|-------|--------|
| **#181** | billing: AMOUNT_TO_PLAN missing autopilot ($150) + professional ($250) | **P0 — governance mandate, 6 consecutive runs** |
| **#185** | CI: 21 pytest failures (pyo3/cryptography PanicException) | env bug, not regression |
| **#169** | [subconscious] Moratorium active — oldest item ~43 days | day 24 |
| #189 | Morning digest 2026-05-27 | closed *(yesterday's digest)* |

*No new issues opened in last 24h.*

---

## Open PRs Needing Action

| # | Title | Age | Action |
|---|-------|-----|--------|
| **#190** | fix(os-workers): inject business profile into worker prompts | today | Review — new draft, post-#188 follow-on |
| **#186** | build(deps-dev): bump @typescript-eslint/parser 8.58→8.60 | 3d | **Safe — merge now** |
| #182 | Split invoices.py god class into 4 service modules | 5d | Draft — blocked on #181 fix first |
| #183 | subconscious: run 33 — GH #181 billing fix (draft) | 4d | Close or merge after #181 resolved |
| #172 | chore(deps-dev): bump eslint 9.39.4→10.4.0 | 10d | Review for breaking changes before merge |
| #11–15 | Dependabot: GH Actions bumps (cache/setup-python/setup-node/create-pr/upload-artifact) | 44d | **Safe batch merge — 5 min** |

---

## Subconscious — Run 37 Recommendation

**Winner:** Add billing-constant-guard as pre-commit Check 11 (WARNING mode, 10-line bash)

- Validates `AMOUNT_TO_PLAN` in `billing.py` contains 4 required keys: `{9900, 15000, 25000, 89900}`
- WARNING-only (same class as Check 5) — does NOT block commits
- **Status: NOT YET IMPLEMENTED** — `033fc3b` committed the run summary but nightly review did not add the hook block to `scripts/hooks/pre-commit`
- Implementation: ~3 min, autonomous. See `subconscious/runs/2026-05-28/winning-concept.md` for exact bash block

**Run 36 standing:** `post-split-test-repair` SKILL.md — confirmed NOT created despite 3 occurrences (`5f2cd2b`, `4afb3cf`, `bca2082`). Nightly review keeps skipping it. Needs explicit session.

---

## Top 3 Priorities

1. **Fix GH #181** (~15 min) — `billing.py:263` add `15000: "autopilot"` + `25000: "professional"` to `AMOUNT_TO_PLAN`. Remove inverted test assertions in `test_billing_amount_to_plan.py:38-44`. P0, 6 consecutive governance runs. Pre-condition for email_sequences split.

2. **Add pre-commit Check 11** (~3 min) — Paste bash block from `subconscious/runs/2026-05-28/winning-concept.md` into `scripts/hooks/pre-commit`. Autonomous. Should have been done by nightly review — wasn't.

3. **Moratorium Sprint Items A/B/D** (~40 min) — Day 24, exit threshold 2. Items: check_project_invariants pre-commit Check 10 (~5 min), widget sync guard (~15 min), CI eval workflow (~20 min).

**Bonus (safe, fast):** Merge #186 + batch #11–15 (~5 min total, zero risk).

---

## Health

| Signal | Status |
|--------|--------|
| Prod code (24h) | Agent OS Groups A+B+C landed (#188) ✓ |
| Open billing bug | #181 — P0, 6 governance runs, UNRESOLVED |
| Pre-commit Check 11 | NOT added (run 37 winner, not implemented) |
| post-split-test-repair skill | NOT created (run 36 winner, nightly keeps skipping) |
| New PR | #190 business profile injection — review needed |
| CI | pyo3 env bug (#185) — not regression, no action |
| KB | ~23 days stale (last compile 2026-05-05) |
| Moratorium | Day 24, Items A/B/D pending |
| Agent OS | PRs #188 merged ✓, #190 new draft |

*Full logs: `ops/routines/logs/nightly-commit-review-2026-05-28.md`, `subconscious/runs/2026-05-28/`*
