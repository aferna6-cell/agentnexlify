# Morning Digest — 2026-05-27

**Generated:** 2026-05-27 UTC
**Moratorium:** DAY 22+ — Items A/B/D still pending
**Run series:** subconscious run 36 complete

---

## Commits (last 24h)

- `2de95c8` subconscious: run 36 (2026-05-27) — Create post-split-test-repair SKILL.md *(autonomous, LOW-risk, .md only)*
- `9465f66` ops: nightly-commit-review 2026-05-27
- `20b79ba` subconscious: run 35 (2026-05-26-pm) — Invoke /god-class-splitter on email_sequences.py *(recommendation only, not yet executed)*

**3 commits. All automated. Zero production code changes.**

---

## Issues — Actionable Open

| # | Title | Labels | Status |
|---|-------|--------|--------|
| **#181** | billing: AMOUNT_TO_PLAN missing autopilot ($150) + professional ($250) | billing, medium-risk | **OPEN — P0, governance mandate, 5 consecutive runs** |
| **#185** | CI: 21 pytest failures (pyo3/cryptography PanicException) | bug, ci, tooling | OPEN — env bug, not code regression |
| **#169** | [subconscious] Moratorium active — oldest item ~41 days | nightly-review | OPEN — day 22+ |
| **#188** | feat(os): Agent OS Group A bridge + Group B sms | *(none)* | OPEN DRAFT — new today |

Total open issues: 110+

---

## Open PRs Needing Action

| # | Title | Age | Draft | Action |
|---|-------|-----|-------|--------|
| #188 | feat(os): Agent OS — Group A bridge config + Group B sms.send | ~1d | ✓ | Review post-moratorium |
| #177 | feat(agent-os): chat-first Agent OS — spec + P0 foundation | 6d | ✓ | Review post-moratorium |
| #182 | Split invoices.py god class into 4 service modules | 4d | ✓ | Review — prerequisite: #181 fix |
| #183 | subconscious run 33 — GH #181 billing fix context | 3d | ✓ | Context-only, can merge or close |
| #186 | bump @typescript-eslint/parser 8.58→8.60 | 2d | ✗ | **Safe — merge now** |
| #15 | bump actions/upload-artifact 4→7 | 42d+ | ✗ | **Safe — merge batch** |
| #14 | bump actions/setup-node 4→6 | 42d+ | ✗ | **Safe — merge batch** |
| #13 | bump peter-evans/create-pull-request 6→7 | 42d+ | ✗ | **Safe — merge batch** |
| #12 | bump actions/setup-python 5→6 | 42d+ | ✗ | **Safe — merge batch** |
| #11 | bump actions/cache 4→5 | 42d+ | ✗ | **Safe — merge batch** |

---

## Subconscious Recommendation — Run 36

**Winner:** Create `.claude/skills/post-split-test-repair/SKILL.md`
→ **ALREADY IMPLEMENTED** (commit `2de95c8`) by nightly review. ✓

**Summary:** 8-step checklist to repoint stale `@patch` decorators and import paths after any god-class split. Pattern fired twice in one week (commits `5f2cd2b` + `4afb3cf`). Skill encodes the repair before email_sequences.py split generates the next round.

**Run 35 winner (still active):** Invoke `/god-class-splitter` on `email_sequences.py` (1255L → 3 modules: email_crud, email_enrollment, email_processor). Pre-condition: fix GH #181 first (~15 min).

---

## KB Health

- Last compile: 2026-05-05 (22 days stale)
- Discover: blocked — network sandbox denies outbound
- Embeddings: blocked — no VOYAGE_API_KEY in cron
- 4 slugs pending backfill: run `python3 scripts/reindex_contextual.py` when SUPABASE_ACCESS_TOKEN available

---

## Top 3 Priorities

1. **Fix GH #181** — billing AMOUNT_TO_PLAN gap. 5 consecutive governance mandates. ~15 min.
   - `backend/routers/billing.py` line ~264: add `15000: "autopilot"`, `25000: "professional"`
   - `backend/tests/test_billing_amount_to_plan.py` lines 38–44: remove backwards assertions, add correct ones
   - Verify: active autopilot/professional Stripe subs have `metadata.plan` set before merge
   - Pre-condition for email_sequences.py split

2. **`/moratorium-sprint` Items A/B/D** — day 22+. ~40 min total. One command.
   - A: Wire `check_project_invariants.py` into pre-commit (~5 min)
   - B: `scripts/check-widget-sync.sh` + pre-push hook (~15 min)
   - D: `.github/workflows/lead-qualifier-eval.yml` (~20 min)
   - Sketches: `subconscious/runs/2026-05-18/winning-concept.md`

3. **Merge safe dep PRs** — #186 + batch #11/#12/#13/#14/#15. ~5 min. Zero risk.
   - All patch/minor GH Actions bumps
   - #186 is a safe parser bump (8.58→8.60)

---

## Health Dashboard

| Signal | Status |
|--------|--------|
| Prod code commits (24h) | 0 |
| Autonomous skill created | ✓ post-split-test-repair (run 36) |
| Open billing bug | #181 — P0, 5 governance runs |
| CI health | #185 — pyo3 env bug (not code regression) |
| KB last compile | 2026-05-05 (22d stale) |
| Moratorium | Day 22+ — Items A/B/D pending |
| Open PRs (safe to merge) | #186 + #11–15 (6 total) |
| Agent OS progress | PRs #177 + #188 in flight (drafts) |

---

*Subconscious runs: `subconscious/runs/2026-05-27/`, `subconscious/runs/2026-05-26-pm/`*
*Nightly review: `ops/routines/logs/nightly-commit-review-2026-05-27.md`*
