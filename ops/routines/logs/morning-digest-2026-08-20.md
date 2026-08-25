# Morning Digest — 2026-08-20

Generated: 2026-08-20 UTC | Caveman mode

---

## Commits (last 24h)

- `e948946` subconscious: run 2026-08-20 (#108) — Step 9J Dependabot auto-merge in nightly SKILL.md
- `e092f14` ops: nightly-commit-review 2026-08-20 [skip ci]
- `2e4dc26` ops: morning-digest 2026-08-19 [skip ci]

---

## Issues Opened / Updated (last 24h)

- **#669** `[security]` Class-wide: 95 routers missing `Depends(block_demo_role)` on mutating endpoints — OPEN (labels: nightly-review, backend, security) — filed 2026-08-20
- **#403** Set `ANTHROPIC_API_KEY` in GitHub Actions secrets — blocks autopilot loop AND KB autopopulate — OPEN (labels: critical, human-action-required, ops) — last updated 2026-08-20 (still unresolved after 42 days)
- **#668** Morning digest 2026-08-19 — OPEN (digest) — filed 2026-08-19

---

## Open PRs Needing Action

| # | Title | Age | Status |
|---|-------|-----|--------|
| #653 | subconscious: runs 102-107 — route-security-guard-audit + Step 9I | 8d | DRAFT — needs merge |
| #666 | bump @typescript-eslint/parser 8.64→8.67 | 3d | Ready — Step 9J should auto-merge |
| #665 | bump eslint 10.7→10.8.1 | 3d | Ready — Step 9J should auto-merge |
| #629 | bump @playwright/test 1.61→1.62.1 | 17d | Ready — Step 9J should auto-merge |
| #630 | bump vite 8.1.5→8.2.0 in demo-platform | 17d | Ready — Step 9J should auto-merge |
| #631 | bump @vitejs/plugin-react 6.0.3→6.0.5 in demo-platform | 17d | Ready — Step 9J should auto-merge |
| #575 | Tenant-silence ops alert + Managed Agents Phase 0 prep | 28d | DRAFT — stale |
| #626 | Step 9G v2: MCP primary KB autopopulate trigger | 18d | DRAFT — stale |
| #648 | kb: drift sweep 2026-08-10 | 10d | DRAFT — review needed |
| #613 | subconscious: runs 2026-07-31 — Step 9G + Step 9I recommendation | 20d | DRAFT — stale |

**5 Dependabot PRs have been sitting 3–17 days.** Step 9J landed last night (e948946) — nightly sweep will handle these going forward. First auto-merge run: tonight.

---

## Subconscious Recommendation (2026-08-20)

**Step 9J implemented** — nightly SKILL.md now merges CI-green Dependabot PRs automatically. Confidence HIGH. Channel proven (Steps 9C/9E/9F/9G/9I all landed same way).

**Bonus action from run 108:** Post diagnostic comment on #403 listing ALL required secrets (ANTHROPIC_API_KEY + SUPABASE_URL + SUPABASE_ANON_KEY) — ANTHROPIC_API_KEY was added but KB still stale 24h later, suggesting second blocker exists.

Previous (2026-08-19): Step 9I (demo-role security sweep) implemented and filed #669 confirming 95 routers exposed.

---

## KB Health

Last logged entry: 2026-07-23 (manual catch-up). 124 articles. Embeddings still deferred (VOYAGE_API_KEY owner-gated). KB autopopulate blocked by #403.

---

## Top 3 Priorities Today

1. **Fix #403 — GitHub Actions secrets** — Add `SUPABASE_URL` + `SUPABASE_ANON_KEY` (and confirm `ANTHROPIC_API_KEY` already set). KB autopopulate has been broken 42+ days. Run subconscious recommends posting diagnostic comment to unblock. Go to: repo Settings → Secrets → Actions.

2. **#669 — Demo-role security gap** — 95 routers missing `Depends(block_demo_role)` on mutating endpoints. Class-wide exploit surface. Step 9I filed the issue; now needs a fix PR. Grep target: `backend/routers/`. Add `block_demo_role` dep to all POST/PUT/DELETE/PATCH routes not already covered.

3. **Merge or close stale draft PRs** — #575 (28d), #626 (18d), #613 (20d) are DRAFT and not progressing. Decide: merge, close, or assign. Each is blocking a cleaner PR queue. Step 9J handles Dependabot; these need human call.
