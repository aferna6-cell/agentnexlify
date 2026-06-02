# Morning Digest — 2026-06-02

**Generated:** 2026-06-02 UTC | **Moratorium day:** 32 | **Pending items:** 15

---

## Commits (last 24h) — 5 total

- `01ad0ee` subconscious: run 2026-06-02 (run 46) — Execute Item A in interactive session
- `90f7387` ops: nightly-commit-review 2026-06-02
- `82f4627` subconscious: run 2026-06-01-pm (run 45) — Execute scope fix + Item A wiring as single human commit
- `4d9263b` ops: kb-drift sweep 2026-06-01 — no drift detected
- `c5746bd` ops: morning-digest 2026-06-01

All ops/subconscious. Zero production code commits.

---

## Issues (open, recently active)

| # | Title | State |
|---|-------|-------|
| #195 | Morning digest 2026-06-01 | OPEN |
| #194 | Em-dash violations in UI copy blocking Item A | OPEN |
| #193 | [subconscious] Moratorium active: 13 pending items, oldest 44 days | OPEN |
| #185 | CI: 21 pre-existing pytest failures (pyo3/cryptography PanicException) — env, not code | OPEN |
| #181 | billing: AMOUNT_TO_PLAN missing autopilot ($150) + professional ($250) entries | OPEN |
| #169 | [subconscious] Moratorium active: 5 pending items, oldest 30 days | OPEN |

---

## Open PRs needing action

| # | Title | Age | Draft | Action |
|---|-------|-----|-------|--------|
| #190 | fix(os-workers): inject business profile into worker prompts | 5d | Yes | Review when moratorium lifts |
| #186 | bump @typescript-eslint/parser 8.58→8.60 | 8d | No | **Safe to merge** |
| #183 | subconscious run 33 — GH #181 billing fix | 9d | Yes | Blocked — billing.py path unknown |
| #182 | Split invoices.py god class into 4 service modules | 10d | Yes | Blocked — moratorium |
| #172 | bump eslint 9.39→10.4 | 15d | No | Major version — check breaking changes before merge |
| #15 | chore(deps): bump actions/upload-artifact 4→7 | 49d | No | Dependabot — batch with #11–14 |
| #14 | chore(deps): bump actions/setup-node 4→6 | 49d | No | Dependabot — batch |
| #13 | chore(deps): bump peter-evans/create-pull-request 6→8 | 49d | No | Dependabot — batch |
| #12 | chore(deps): bump actions/setup-python 5→6 | 49d | No | Dependabot — batch |
| #11 | chore(deps): bump actions/cache 4→5 | 49d | No | Dependabot — batch |

---

## Subconscious (Run 46) — HIGH confidence

**Recommendation:** Execute Item A **this session**. 4th consecutive run. Interactive session = highest-probability window.

- Edit `scripts/check_project_invariants.py` — skip `.jsx`/`.tsx` in em-dash walk (3 lines)
- Add Check 10 to `scripts/hooks/pre-commit` (3 lines bash)
- Commit → closes GH #194, moratorium pending 15 → 13

**Run 47 mandate:** If Item A NOT done this session → run 47 winner = Item D AUTONOMOUS-EXECUTABLE (create `.github/workflows/lead-qualifier-eval.yml`). Mechanism switch binding at 5 consecutive failures.

**New finding (run 46):** `backend/services/billing.py` not found at expected path post-god-class refactor (PR #180). Two prior GH #181 fix attempts targeted wrong file. Must `find backend -name "*billing*"` before any fix attempt.

---

## KB Health

No new articles ingested today. Last compile: 2026-05-05, 15 articles. Embeddings backlog: 4+ articles pending Supabase re-auth + Voyage key in cron env.

---

## Nightly Review (2026-06-02)

- Commits reviewed: 7 | Issues opened: 0 | Autonomous fixes: 0
- Invariants: **FAIL** — em-dash in 5 JSX files (intentional UI copy, tracked GH #194)
- No production bugs. All commits ops/docs/subconscious.

---

## Top 3 Priorities Today

**1. Execute Item A (~10 min) — URGENT**
Scope `check_project_invariants.py` em-dash check to skip `.jsx`/`.tsx` + wire Check 10 to `scripts/hooks/pre-commit`. Implementation sketch fully pre-written in `subconscious/runs/2026-06-02/winning-concept.md`. Run `python3 scripts/check_project_invariants.py` after edit — expect 6 PASS, exit 0. Closes GH #194.

**2. Investigate billing.py location (~5 min)**
```bash
find backend -name "*billing*" -type f
grep -rn "AMOUNT_TO_PLAN" backend/
```
If `{9900, 15000, 25000, 89900}` all present → GH #181 already resolved, close it. If missing entries at new path → update GH #181 sketch, fix takes ~10 min.

**3. Merge PR #186 + batch Dependabot PRs (~10 min)**
`@typescript-eslint/parser 8.58→8.60` is safe minor bump. Batch-merge Dependabot `#11–#15` (CI action bumps, all pinned). Clears 6 PRs from backlog.
