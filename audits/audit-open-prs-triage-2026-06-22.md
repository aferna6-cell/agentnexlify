# Open PR Triage — 2026-06-22

48 PRs were open against `main` before this session's fix-PRs (#347 rate-limit,
#348 CI budget, #349 plan-catalog wiring). This triages every one with a
disposition. **Execution is gated on #348 merging + the Actions-minute reset** —
without CI, dependency bumps can't be validated, and `main` auto-deploys to
Railway + Vercel. Until then, merge only what `scripts/ci-local.sh` (or a
targeted local run) can verify.

Legend: **MERGE-SAFE** (low risk, land after CI green) · **MAJOR** (breaking dep,
separate validated effort) · **REVIEW** (feature work, needs author/owner review)
· **CLOSE?** (likely stale/superseded — confirm before closing) · **HOLD**.

## A. Dependabot — dev-only deps (MERGE-SAFE once CI green)
Build/test tooling; no production-runtime impact. Land as a batch.

| PR | Bump | Note |
|----|------|------|
| #342 | vitest 4.1.8→4.1.9 (frontend) | patch |
| #281 | @vitest/coverage-v8 4.1.8→4.1.9 (frontend) | patch; keep in lockstep with vitest |
| #279 | vitest 4.1.8→4.1.9 (demo) | patch |
| #277 | @vitest/coverage-v8 4.1.8→4.1.9 (demo) | patch |
| #340 | @typescript-eslint/parser 8.58→latest | minor; lint-only |
| #273 | @playwright/test 1.60→1.61 | minor; e2e-only |

## B. Dependabot — runtime deps (MERGE-SAFE but verify import/boot)
Affect the shipped backend. Land individually after a local import/boot smoke.

| PR | Bump | Note |
|----|------|------|
| #284 | python-jose >=3.3.0 | auth/JWT — smoke `_create_token` round-trip |
| #282 | stripe <12,>=11 | billing — run billing tests before merge |
| #17 | python-json-logger 3→4 | logging — boot smoke |
| #102 | youtube-transcript-api | KB ingest — low blast radius |

## C. Dependabot — MAJOR (separate validated efforts, do NOT batch)
| PR | Bump | Risk |
|----|------|------|
| #275 | react 18→19 (frontend) | breaking; full dashboard regression needed |
| #274 | react-dom 18→19 (frontend) | pair with #275 |
| #280 | react 18→19 (demo) | breaking |
| #278 | react-dom 18→19 (demo) | pair with #280 |
| #271 | eslint 9→10 | flat-config / rule breakage likely |
| #283 | uvicorn 0.34→0.49 | server runtime; big jump — test boot + workers |
| #65 | cross-env 7→10 | dev; major but low risk |
| #30 / #22 | react-helmet-async 2→3 | duplicate PRs — close one |

## D. Dependabot — GitHub Actions versions (MERGE-SAFE; touch workflows)
Coordinate with #348 (CI changes). Verify against the post-#348 workflow files.

| PR | Bump |
|----|------|
| #15 | actions/upload-artifact 4→7 |
| #14 | actions/setup-node 4→6 |
| #13 | peter-evans/create-pull-request 6→? |
| #12 | actions/setup-python 5→6 |
| #11 | actions/cache 4→5 |

## E. Feature work (REVIEW — author/owner decision)
| PR | Title | Disposition |
|----|-------|-------------|
| #333 | main-pending: 51 commits rollup | Likely **superseded** — main now carries the session merges. Verify `git diff` vs main; CLOSE if empty. |
| #328 | Billing save-offer before cancel | REVIEW — retention feature |
| #327 | AI Workforce upgrade prompt on 402 | REVIEW — pairs with the plan-gate work |
| #325 | Checkout fixes (Stripe Link emails) | REVIEW — billing |
| #286 | Agent OS fail/abstain alerts | REVIEW |
| #270 | Integrations keys UI + widget_chat god-class split | REVIEW — large; needs CI |
| #212 | OS web-grounded research worker | REVIEW |
| #211 | Agent OS north-star (Act/learning) | REVIEW |
| #190 | os-workers business profile inject | REVIEW — small |
| #182 | invoices.py god-class split | REVIEW — large refactor; needs CI |
| #85 | intent engineering layer | REVIEW — large |
| #80 | onboarding-v2 Week 1 | REVIEW — large |
| #71/#72/#73/#74 | memory-hygiene set | REVIEW — small, batchable |
| #2 | restaurant menu operator precedence fix | MERGE-SAFE — small bug fix; verify locally |

## F. Automation / housekeeping drafts (CLOSE? — confirm)
Auto-generated improvement drafts that accumulate. Confirm none carry a wanted fix, then close stale ones.

| PR | Title |
|----|-------|
| #341 | kb: drift sweep 2026-06-22 |
| #260 | pre-commit Check 10 + governance |
| #258 | remove em dashes from landing page |
| #209 | subconscious run 52 — timing-safe token compare |
| #200 | subconscious run 49 |
| #183 | subconscious run 33 |
| #86 | hooks: 4 missing post-edit checks |

Note: #209 (timing-safe token comparison) may be a real security fix — review before closing.

## Recommended execution order (after #348 merges + minutes reset)
1. **Batch A** (dev-dep patches) — single CI pass, merge together.
2. **Batch D** (Actions versions) — after #348, re-validate workflows.
3. **Batch B** (runtime deps) — one at a time with boot/billing smoke.
4. **#2** + **#71–74** — small, safe.
5. **Close** confirmed-stale items in F (keep #209 for security review).
6. **Verify #333** vs main; close if superseded.
7. **MAJOR (C)** + large features (E) — individual validated efforts, not in scope for a batch.

## Why nothing is merged/closed in this PR
This PR is the triage record only. Bulk-merging deps with CI down risks a broken
`main` (auto-deploys to prod); bulk-closing others' drafts risks discarding wanted
work (e.g. #209). Each batch above should be executed deliberately once CI is
restored (#348) — ideally green-lit per batch.
