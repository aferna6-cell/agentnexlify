# Morning Digest — 2026-08-28

Generated: 2026-08-28 UTC | Caveman mode

---

## Commits (last 24h)

- `d36fc91` subconscious: run 2026-08-28 — Fix Step 9J: add @dependabot rebase trigger for unknown mergeable_state
- `08c3eb4` ops: nightly-commit-review 2026-08-28
- `245dacf` ops: morning-digest 2026-08-27

**Key action:** Subconscious run 111 mandate executed — Step 9J rebase trigger shipped today. This activates the Dependabot auto-merge loop that was at 0% effectiveness (all 20+ PRs in `unknown` state). Next nightly should show first merges.

---

## Issues — Open / Updated (last 24h)

| # | Title | Labels | Age |
|---|-------|--------|-----|
| #684 | Brain connector 36d stale — last run 2026-07-23 | human-action-required, brain-connector | 36d |
| #689 | Code quality: silent exception blocks in churn_watch.py / appointment_booker.py | nightly-review, risk:low | 2d |
| #688 | Morning digest 2026-08-26 | digest | 2d |
| #687 | Voice addon double-billing: no cancellation when tenant upgrades to agent_os | nightly-review, billing, risk:medium | 2d |
| #669 | [security] 95 routers missing Depends(block_demo_role) on mutating endpoints | ai-ready, security | 8d |
| #403 | Set ANTHROPIC_API_KEY in GitHub Actions secrets | critical, human-action-required | **50d** |
| #399 | AUTOPILOT_GH_TOKEN expired — autopilot loop dead | human-action-required | **50d** |

**Flagged:**
- #403 — Day **50**. Critical. Blocks autopilot loop + KB autopopulate. Still no action.
- #687 — MEDIUM billing bug. Voice addon not cancelled on agent_os upgrade. Double-charge possible.
- #684 — Brain connector dead 36 days. Second brain degrading silently.
- #669 — 95 security-unguarded endpoints. Middleware in PR #683 waiting.

---

## Open PRs Needing Action

| # | Title | Age | State |
|---|-------|-----|-------|
| #683 | subconscious: runs #110-111 — Step 9K stale PR closer + pre-commit block_demo_role hook | 4d | Draft |
| #690 | docs(outreach): record live Instantly campaign email templates | 2d | Draft |
| #679 | chore(deps-dev): bump eslint 10.7.0 → 10.9.0 | 4d | Ready |
| #666 | chore(deps-dev): bump @typescript-eslint/parser 8.64.0 → 8.67.0 | 11d | Ready |
| #629 | chore(deps-dev): bump @playwright/test 1.61.1 → 1.62.1 | 25d | Ready |
| #631 | chore(deps-dev): bump @vitejs/plugin-react 6.0.3 → 6.0.5 in /demo-platform | 25d | Ready |
| #630 | chore(deps-dev): bump vite 8.1.5 → 8.2.0 in /demo-platform | 25d | Ready |
| #653 | subconscious: runs 102-110, Step 9J implemented | 16d | Draft (superseded by #683) |
| #648 | kb: drift sweep 2026-08-10 | 18d | Draft (stale) |
| #626 | subconscious: run 109 — Step 9G v2 | 26d | Draft (stale) |
| #575 | Tenant-silence ops alert + Managed Agents Phase 0 prep | **36d** | Draft (STALE) |

**Action needed:**
- Merge patch Dependabot PRs (#679, #666, #629, #631, #630) — Step 9J rebase trigger will fire on next nightly, should auto-merge. Watch tonight.
- Close stale draft PRs #653, #648, #626, #575 — superseded or no-longer-relevant.
- Merge #683 when ready — contains Step 9K + block_demo_role pre-commit hook (security fix for #669).

---

## Subconscious — Run 110/111 (2026-08-28)

**Winning concept shipped:** Step 9J rebase trigger (`d36fc91`).

- Run 109 added Dependabot auto-merge logic (Step 9J).
- First nightly: 0 merges — all 20+ Dependabot PRs in `mergeable_state: unknown`.
- Root cause: GitHub doesn't compute mergeability until asked. Fix: post `@dependabot rebase` comment (dedup guard + cap 5/run).
- Fix committed this morning. Next nightly (tonight) should see first auto-merges.

**Run 111 mandate checklist:**
- [ ] `grep 'triggered rebase on PR' ops/routines/logs/nightly-commit-review-*.md` — did trigger fire?
- [ ] Count rebase triggers (cap: 5 per run)
- [ ] Any Dependabot PRs become `clean` + merged within 24-48h?
- [ ] #669 middleware: PR #683 merged? If not, check issue-to-pr-loop status.
- [ ] #684 brain connector: SUPABASE_ACCESS_TOKEN set in Railway yet?
- [ ] #403 / #399: still open → escalate to human.

---

## KB — Last 24h

- 2026-08-26 08:18 — discover+compile, 4 new wiki articles
- 2026-08-26 19:28 — discover+compile, 4 new wiki articles
- 2026-08-27: no new runs logged (weekend?)
- Embeddings skipped all runs (no VOYAGE_API_KEY in cron env). FTS fallback active.
- Estimated index: ~132 articles.

---

## Top 3 Priorities Today

**1. Fix GH #403 — ANTHROPIC_API_KEY in GitHub Actions (human action, 50 days)**
- Day 50. Nothing changes until this is done.
- Blocks: autopilot loop, KB autopopulate cron, nightly CI validation.
- Action: GitHub repo → Settings → Secrets and variables → Actions → New secret → `ANTHROPIC_API_KEY`.
- Also: #399 AUTOPILOT_GH_TOKEN expired — same place, same day.

**2. Triage GH #687 — Voice addon double-billing bug (billing, risk:medium)**
- Real money at risk. Nightly caught: voice addon not cancelled when tenant upgrades to agent_os.
- PR #683 may cover pre-commit hook for security but not this billing logic.
- Action: read #687 body, open fix PR targeting `backend/services/stripe_service.py`, ship this sprint.

**3. Close stale draft PRs — #575, #653, #648, #626 (36d, 16d, 18d, 26d)**
- Accumulating debt. Step 9K (stale PR closer in PR #683) will handle this on next nightly once #683 merges.
- Short-circuit: manually close #575 (Managed Agents Phase 0, 36d stale, superseded by live Managed Agents work).
- Or merge #683 today so Step 9K auto-closes the rest tonight.
