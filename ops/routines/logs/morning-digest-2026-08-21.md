# Morning Digest — 2026-08-21

Generated: 2026-08-21 UTC | Caveman mode.

---

## Commits (last 24h)

- `95d1c87` ops: nightly-commit-review 2026-08-21 [skip ci]

1 commit. Nightly review ran and committed its log.

---

## Issues (opened/updated last 24h)

- **#669** [security] 95 routers missing `Depends(block_demo_role)` on mutating endpoints — OPEN | labels: security, nightly-review, backend | updated 2026-08-21. Systemic. Step 9I sweep found 97 routers; 95 lack guard. Filed 2026-08-20.
- **#670** Morning digest 2026-08-20 — OPEN | digest
- **#403** Set ANTHROPIC_API_KEY in GitHub Actions — OPEN | critical, human-action-required, ops | updated 2026-08-20. 43 days old. Blocks KB autopopulate + autopilot loop. Per subconscious run 108: also needs SUPABASE_URL + SUPABASE_ANON_KEY — likely second blocker.

---

## Open PRs Needing Action

Dependabot (6 aging — no merge yet):
- **#666** bump @typescript-eslint/parser 8.64→8.67 | 4 days old | not draft
- **#665** bump eslint 10.7→10.8.1 | 4 days old | not draft
- **#630** bump vite 8.1.5→8.2.0 in /demo-platform | 18 days old | not draft
- **#631** bump @vitejs/plugin-react 6.0.3→6.0.5 in /demo-platform | 18 days old | not draft
- **#629** bump @playwright/test 1.61.1→1.62.1 | 18 days old | not draft
- **#596** update fastapi >=0.140.7,<0.141 in /backend | 25 days old | not draft

Subconscious / ops (stale drafts):
- **#653** subconscious runs 102-110 + Step 9J implemented | draft | 9 days old | updated TODAY (2026-08-21) — active
- **#671** ops: morning-digest 2026-08-20 | draft | 1 day old
- **#575** Tenant-silence ops + Managed Agents Phase 0 prep | draft | 29 days old — stale
- **#626** subconscious run 109 — Step 9G v2 KB autopopulate | draft | 19 days old
- **#648** kb: drift sweep 2026-08-10 | draft | 11 days old
- **#613** subconscious runs 2026-07-31 — Step 9G/9I | draft | 21 days old
- **#611** subconscious run 2026-07-30 — Step 9H | draft | 22 days old
- **#606** subconscious run 101 — feature-docs-trio | draft | 24 days old
- **#604** deps: lift fastapi <0.136 cap | draft | 24 days old

**14 open PRs total. 6 Dependabot aging. Multiple stale subconscious drafts.**

---

## Knowledge Base

- Last real update: 2026-07-23 (manual catch-up, 8 articles compiled, INDEX 114→124)
- No KB activity last 24h — blocked by missing GH Actions secrets (#403)
- FTS fallback active; embeddings deferred (no VOYAGE_API_KEY)

---

## Subconscious Recommendation (2026-08-20)

**Step 9J — Dependabot auto-merge in nightly-commit-review SKILL.md.**

Status: AUTONOMOUS-EXECUTABLE. Mandate-triggered (run_108_mandate named 9J explicitly). 6 Dependabot PRs aging. 4 consecutive morning digests flagged same PRs — zero action taken. Once added: CI-green Dependabot PRs merge automatically within 24h forever. PR #653 shows Step 9J already in that branch — confirm landed in SKILL.md.

Prior run (2026-08-19): Step 9I (demo-role security sweep) — IMPLEMENTED. GH #669 filed 2026-08-20 with 95 violations found on first sweep. Step working.

---

## Top 3 Priorities Today

1. **Fix #403 — Set GitHub Actions secrets** (critical, 43 days old)
   - Add: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` to repo secrets
   - Unblocks: KB autopopulate (stale since 2026-07-23) + autopilot loop
   - Where: GitHub repo Settings → Secrets and variables → Actions
   - Note: ANTHROPIC_API_KEY alone may not be enough — subconscious run 108 flagged SUPABASE creds as likely second blocker

2. **Address #669 — 95 routers missing block_demo_role** (security, systemic)
   - Step 9I sweep found 97 routers; 95 lack `Depends(block_demo_role)` on POST/PUT/DELETE/PATCH
   - Two individual violations already filed (#643, #661) — now confirmed class-wide
   - Action: plan a bulk fix pass (compound-engineering + TDD) — one PR, all 95 routers

3. **Merge Dependabot PRs** (#629, #630, #631, #665, #666, #596)
   - All 6 are non-draft, CI should be checkable
   - Step 9J (subconscious 2026-08-20) will automate this going forward — check PR #653 to confirm it landed
   - Manual action today: verify CI green → merge all 6

---

## Blockers

- GitHub Actions secrets missing → KB autopopulate dead, autopilot loop dead (#403, 43 days)
- 95 routers lack demo-role guard (#669, filed yesterday)
- 6 Dependabot PRs aging (security dep exposure window)
