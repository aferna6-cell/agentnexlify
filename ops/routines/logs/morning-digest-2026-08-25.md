# Morning Digest — 2026-08-25

Generated: 2026-08-25 (automated routine)

---

## Commits (last 24h)

- `5bc0288` ops: correct Step 9J result in nightly-commit-review-2026-08-25
- `5cdc0c1` ops: nightly-commit-review 2026-08-25
- `3875310` subconscious: run #109 — Step 9J Dependabot auto-merge (#674)
- `ed1553f` ops: morning-digest 2026-08-20 (#671)
- `ecb6653` ops: morning-digest 2026-08-21 (#673)
- `1c49ac5` ops: morning-digest 2026-08-24 (#676)
- `6fe6efc` kb: drift sweep 2026-08-24 (#681)
- `4c45e67` fix(ci): unschedule the remaining 11 workflows (#682)
- `334d32c` fix(ci): unschedule replaced workflows, close the local-gate gaps (#680)
- `decc1e9` fix(agents): stop confirming appointments that do not exist (#678)
- `08e9178` Managed-agents audit + fixes for all 7 findings (#677)
- `9709afe` chore: weekly skill discovery report 2026-08-24

---

## Issues Opened/Updated (last 24h)

- **#684** [OPEN] Brain connector 33 days stale — last run 2026-07-23 `[human-action-required, operational, brain-connector]` — opened today
- **#403** [OPEN] Set ANTHROPIC_API_KEY in GitHub Actions secrets — blocks autopilot loop AND KB autopopulate `[critical, human-action-required, ops]` — bumped by nightly review
- **#669** [OPEN] [security] Class-wide: 95 routers missing Depends(block_demo_role) on mutating endpoints `[ai-ready, nightly-review, backend, security]` — updated today
- **#675** [OPEN] Morning digest 2026-08-24 `[digest]`

---

## Open PRs Needing Action

| # | Title | Age | Status |
|---|-------|-----|--------|
| #683 | subconscious: run #110 — Step 9K stale PR closer + major-version safety gate | 1d | draft — fresh, review |
| #575 | Tenant-silence ops alert + Managed Agents Phase 0 prep | 33d | draft — very stale |
| #679 | chore(deps-dev): bump eslint 10.7→10.9.0 | 1d | open — CI unknown, skip merge |
| #653 | subconscious: runs 102-110 — Step 9J implemented + GH #669 middleware proposal | 13d | draft |
| #666 | chore(deps-dev): bump @typescript-eslint/parser 8.64→8.67.0 | 8d | open — CI unknown |
| #626 | subconscious: run 101 Step 9G v2 — MCP primary KB autopopulate trigger | 23d | draft — stale |
| #648 | kb: drift sweep 2026-08-10 | 15d | draft — stale |
| #630 | chore(deps-dev): bump vite 8.1.5→8.2.0 in /demo-platform | 22d | open — aging Dependabot |
| #631 | chore(deps-dev): bump @vitejs/plugin-react 6.0.3→6.0.5 /demo-platform | 22d | open — aging Dependabot |
| #629 | chore(deps-dev): bump @playwright/test 1.61.1→1.62.1 | 22d | open — aging Dependabot |

**Dependabot note:** Step 9J (auto-merge) ran last night. All eligible PRs had `mergeable_state: "unknown"` — 0 merged. CI must clear before next nightly fires them.

---

## Subconscious Recommendation

Run #109 (2026-08-24): **Step 9J Dependabot auto-merge added to nightly-commit-review SKILL.md** — autonomous-executable via 1st carry-forward mandate. First live execution ran 2026-08-25 nightly; 0 PRs merged (CI `unknown`). Expect merges on next nightly once CI evaluates open Dependabot PRs.

Run #110 mandate items outstanding:
1. Verify Step 9J fired correctly in today's nightly log ✓ (0 merged — CI block, expected)
2. GH #669 — 97 routers missing `block_demo_role` — still open, no middleware PR yet
3. GH #403 — KB/autopilot stale 33d — human action required (rotate API keys)
4. Step 9K candidate — stale autonomy PR closer — tracked in PR #683

---

## Top 3 Priorities for Today

### 1. CRITICAL: Rotate secrets (GH #403 + GH #684) — human action required
- `ANTHROPIC_API_KEY` + `SUPABASE_ACCESS_TOKEN` stale in GH Actions — 33 days
- Blocks: KB autopopulate, brain connector refresh, autopilot loop
- Fix: rotate in GH repo secrets → re-run `bash scripts/daily/kb-autopopulate.sh` + `brain/_tools/refresh_connectors.py`

### 2. HIGH: Review and merge PR #683 (subconscious run #110)
- Step 9K: stale PR closer + major-version safety gate
- 1 day old, draft — read it, approve + merge if clean
- Also closes out compounding subconscious PR debt (#575, #626, #648 all stale)

### 3. HIGH: GH #669 — 97 routers missing block_demo_role middleware
- Security issue, ai-ready, nightly-flagged
- Subconscious proposed a middleware solution (PR #653)
- Decide: accept the middleware approach or handle differently — this is blocking clean security posture

---

## Health Snapshot

| Signal | Status |
|--------|--------|
| CI / GH Actions | Dark since 2026-07-20 — local gate only (`scripts/ci_local.sh`) |
| KB autopopulate | Stale 33d (credential block) |
| Brain connector | Stale 33d (credential block) |
| Nightly commit review | Running — fired 2026-08-25 cleanly |
| Subconscious loop | Running — run 109 complete, run 110 PR open |
| Step 9J Dependabot auto-merge | Added to SKILL.md — first run 0 merged (CI unknown) |
| Widget byte-identical check | Not flagged |
| Managed agents | Audit complete, 7 findings fixed (#677) |
