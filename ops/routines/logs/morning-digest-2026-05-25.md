# Morning Digest — 2026-05-25

**Generated:** 2026-05-25 UTC
**Moratorium:** DAY 20+ — items A/B/D still pending

---

## Commits (last 24h)

- `a25f540` ops: nightly-commit-review 2026-05-25 — 3 commits reviewed (1 MEDIUM, 2 LOW), 0 auto-fixes, GH #181 carry-forward

**Zero production code changes. Zero backend/frontend/widget/migration touches.**

---

## Recent Commits (last 48h context)

- `a25f540` ops: nightly-commit-review 2026-05-25 (LOW — ops only)
- `21d66d7` subconscious: run 2026-05-23-pm (run 32) — GH #181 billing fix with CI-trap evidence (LOW — docs only)
- `2174732` Refactor god classes: branding_service, control_center, channels_facebook, pipeline, social_media (#180) (MEDIUM — 31 files, 5038+/2064−, all invariant checks PASS)

---

## Issues (active, non-digest)

| # | Title | Labels | Status |
|---|-------|--------|--------|
| #181 | billing: AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional | billing, medium-risk, nightly-review | **OPEN — action required** |
| #169 | [subconscious] Moratorium active: 5 pending items, oldest 36+ days | nightly-review | OPEN — day 20+ |

107 total open issues. No new feature/bug issues opened in last 24h.

---

## Open PRs Needing Action

All 10 open PRs are dependabot dependency bumps, all 40 days old. **No human-authored PRs open.**

| # | Title | Risk | Action |
|---|-------|------|--------|
| #31 | bump react-dom 18→19.2.5 in demo-platform | MAJOR — React 19 breaking changes | Review before merge |
| #29 | bump react 18→19.2.5 in demo-platform | MAJOR | Review before merge |
| #18 | bump @vitejs/plugin-react 4→6.0.1 in demo-platform | MAJOR (2 major versions) | Review before merge |
| #25 | bump @vitejs/plugin-react 4→6.0.1 in frontend | MAJOR | Review before merge |
| #21 | bump @vitest/coverage-v8 3→4.1.4 in frontend | MAJOR | Review before merge |
| #23 | bump vitest 3→4.1.4 in demo-platform | MAJOR | Review before merge |
| #30 | bump react-helmet-async 2→3.0.0 in frontend | MAJOR | Review before merge |
| #22 | bump react-helmet-async 2→3.0.0 in demo-platform | MAJOR | Review before merge |
| #27 | bump dompurify 3.3.3→3.4.0 in frontend | PATCH | **Safe — merge now** |
| #17 | bump python-json-logger 3.3.0→4.1.0 in backend | MAJOR | Review before merge |

**All MAJOR bumps need frontend/backend build test before merging.** Only #27 (dompurify patch) is safe to merge immediately.

---

## Subconscious Recommendation (Run 32 — 2026-05-23-pm)

**Winner: Fix GH #181 — Add `15000: "autopilot"` + `25000: "professional"` to `AMOUNT_TO_PLAN`, remove CI-blocking contradictory tests.**

- Confidence: HIGH
- Effort: S (~15 min)
- Risk: MEDIUM — billing/payments code, requires human review
- Two consecutive billing commits (c72b535, 1eaaeec) both missed these entries — confirms non-obviousness
- `test_billing_amount_to_plan.py` lines 38-44 now BLOCK any correct fix from passing CI (CI trap wired by 1553bf7)
- Files: `backend/routers/billing.py:263`, `backend/tests/test_billing_amount_to_plan.py:38-44`
- **Human approval required before touching billing code**

Standing signal (run 28+): `/moratorium-sprint` Items A/B/D still pending after 20 days.

---

## KB Health

- Last compile: 2026-05-05 (20 days stale)
- Embeddings: blocked — no `VOYAGE_API_KEY` in cron env, 4 slugs pending backfill
- Fix: `python3 scripts/reindex_contextual.py` when `SUPABASE_ACCESS_TOKEN` available

---

## Top 3 Priorities Today

1. **Fix GH #181** (billing: AMOUNT_TO_PLAN) — Subconscious HIGH confidence. S-effort ~15 min. Two dict entries + four test method edits. APPROVE then run `/fix-bug`. DO NOT merge without verifying active autopilot/professional Stripe subscriptions have `metadata.plan` set.

2. **`/moratorium-sprint` Items A/B/D** — Moratorium day 20+. ~40 min total. One session clears the queue:
   - A: Wire `check_project_invariants.py` into pre-commit (~5 min)
   - B: Create `scripts/check-widget-sync.sh` + pre-push wire (~15 min)
   - D: `.github/workflows/lead-qualifier-eval.yml` CI eval workflow (~20 min)
   Sketches at `subconscious/runs/2026-05-18/winning-concept.md`.

3. **Triage 9 MAJOR dep bumps** (40d stale) — React 18→19 is a breaking change. Run `npm run build` in frontend + demo-platform after each batch. Merge #27 (dompurify) immediately — zero risk.

---

## Health Dashboard

| Signal | Status |
|--------|--------|
| Prod changes (24h) | 0 |
| Nightly bugs found | 0 (3 reviewed, carry-forward only) |
| Open billing bug | #181 — MEDIUM, needs human approval |
| KB last compile | 2026-05-05 (20d stale) |
| Supabase embeddings | Failing (no VOYAGE_API_KEY in cron) |
| Moratorium | DAY 20+ — items A/B/D pending |
| Open PRs | 10 dependabot (all 40d, 9 MAJOR) |
| Open issues | 107 total |

---

*Full nightly review: `ops/routines/logs/nightly-commit-review-2026-05-25.md`*
*Subconscious winning concept: `subconscious/runs/2026-05-23-pm/winning-concept.md`*
