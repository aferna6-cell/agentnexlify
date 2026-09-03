# Morning Digest — 2026-09-03

Generated: 2026-09-03T10:00Z

---

## Commits (last 24h) — 26 commits

- `ead83ba` ops: nightly-commit-review 2026-09-03
- `ff3ab04` feat(m9): Workflow persistence + deterministic engine (M9.2) (#752)
- `2641bed` Merge PR #751 cursor/m9-workflow-contract-a2c9
- `709b088` Revert: chore(ai) auto-commit [m9-workflow-contract 2026-09-02 20:00]
- `5b5d24b` fix(ci): include M9.1 workflow contract tests in PR coverage
- `aa02c9c` chore(ai): auto-commit Claude edits [m9-workflow-contract]
- `59e7b04` fix(m9): enforce risk-aware workflow transition contract
- `47124b1` feat(m9): workflow contract types and transition rules (M9.1)
- `200d07c` Merge PR #750 cursor/governance-m9-start-a2c9
- `3459405` chore(governance): close M8→M9 gate — #669 audit, bot PRs, M9 START
- `afb78de` docs: auto-log bug fix from 17bab2d
- `17bab2d` Merge PR #749 cursor/demo-role-middleware-669-a2c9
- `4ceaaa5` fix(security): central demo-role mutation middleware (GH #669)
- `97c0cbf` docs: auto-log bug fix from 821a049
- `821a049` Merge PR #747 cursor/brace-expansion-audit-fix-a2c9
- `a9d5424` test(vault): cover oauth_integration_payload_for_db dark-vault/no-token branches
- `80d5538` fix(tests): retarget stale patches after module splits for CI green
- `5d33dab` fix(deps): clear high-severity npm audits in frontend and demo-platform
- `e88806a` docs(m8): record M8→CI→#669→M9 transition after #748 merge
- `bce789a` chore(ci): trigger full PR Validation for brace-expansion fix
- `0d72a8f` fix(deps): resolve high-severity brace-expansion audit finding
- `9df8a0e` docs: auto-log bug fix from 1f36818
- `1f36818` Merge PR #748 cursor/m8-input-preservation-a2c9
- `ac80a1b` docs(m8): formal completion evidence on 962da79b [skip ci]
- `962da79` fix(m8): extend Google OAuth state TTL to 60m [skip ci]
- `839e338` fix(m8): preserve send_email input on data-plane outcome write [skip ci]

**Summary:** Heavy M9 push. M8 fully closed. M9.1 (workflow contract types) + M9.2 (persistence + deterministic engine) both merged. Security fix (#669 demo-role middleware) + brace-expansion dep audit cleared.

---

## Issues Updated (last 24h)

- **#403** OPEN `[critical][human-action-required]` — Set ANTHROPIC_API_KEY in GitHub Actions secrets — blocks autopilot loop + KB autopopulate
- **#684** OPEN `[human-action-required][brain-connector]` — Brain connector 33 days stale — last run 2026-07-23
- **#745** OPEN `[digest]` — Morning digest 2026-09-02

**2 human-action-required blockers outstanding. Both need Aidan.**

---

## Open PRs — 10 total

| # | Title | Age | Status |
|---|-------|-----|--------|
| #754 | fix(m9): M9.2 correction — retry/verify semantics + DB integrity | 1d | open |
| #753 | subconscious: run 2026-09-03 — Fix M9.2 dead guard in derive_workflow_status() | 1d | DRAFT |
| #722 | bump eslint 10.7→10.9.1 | 3d | open |
| #721 | bump @typescript-eslint/parser 8.64→8.68 | 3d | open |
| #690 | docs(outreach): Instantly campaign email templates | 8d | DRAFT |
| #648 | kb: drift sweep 2026-08-10 | 24d | DRAFT |
| #631 | bump @vitejs/plugin-react 6.0.3→6.0.5 (demo-platform) | 31d | DRAFT |
| #630 | bump vite 8.1.5→8.2.0 (demo-platform) | 31d | open |
| #629 | bump @playwright/test 1.61.1→1.62.1 | 31d | open |
| #604 | deps: lift fastapi <0.136 cap | 36d | DRAFT |

**Needs action:**
- #754 — non-draft, 1 day old, M9.2 correction — review + merge or wait for CI
- #753 — draft, subconscious fix for M9.2 dead guard — active subconscious PR
- #629/#630/#631 — 31 days stale dependabot; merge or close
- #604 — 36 days stale; merge or close
- #648 — 24 days stale kb drift DRAFT; merge or close

---

## Subconscious Recommendation (Run 114 — 2026-08-31-pm)

**Step 9K: stale subconscious draft PR audit in nightly-commit-review SKILL.md.**
- Add Step 9K block after Step 9J: count open `subconscious/*` PRs, warn ≥3 stale (>30d), escalate comment ≥5 stale or any >60d.
- Bonus fix: repair Step 9J Dependabot detection (use `search_pull_requests` not `list_pull_requests` with creator filter).
- Run 115 verification mandate: confirm Step 9K fires in nightly-2026-09-01 log.

---

## KB Status

- Last compile: 2026-08-26 (4 articles via 18:00 cron: GoHighLevel AI Employee, GHL cost/carrier fees, Managed Agents pricing, Prompt Caching savings)
- No new KB activity in last 24h
- 2 blockers preventing full autopopulate: #403 (ANTHROPIC_API_KEY) + VOYAGE_API_KEY (unset in cron env — embeddings deferred)

---

## Top 3 Priorities Today

1. **Review/merge #754** — M9.2 correction PR (retry/verify semantics + DB integrity). Non-draft, 1 day old. M9 momentum depends on clean correction pass before next M9 feature work.

2. **Fix #403 + #684 (human action)** — Set ANTHROPIC_API_KEY in GH Actions secrets (#403). Check SUPABASE_ACCESS_TOKEN in Railway (#684 brain connector 41 days stale). Both block autonomous loops. Neither can be fixed by agent — Aidan must do these.

3. **Close stale dep PRs (#604, #629, #630, #631)** — Four dependency PRs 31–36 days old. Merge all (no conflicts expected) or batch-close if superseded. Reduces open PR noise ahead of M9 sprint.
