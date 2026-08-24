# Morning Digest — 2026-08-24

Generated: 2026-08-24 UTC | Caveman mode.

---

## Commits (last 24h)

- `25fb0dc` ops: nightly-commit-review 2026-08-24 [skip ci]

1 commit. Quiet night — nightly-commit-review fired and logged. No code changes.

---

## Issues (open, recently active)

**CRITICAL / human-action-required — BLOCKED ON YOU:**
- #403 `Set ANTHROPIC_API_KEY in GitHub Actions secrets` — open since 2026-07-09. Blocks KB autopopulate + autopilot loop in CI. 46 days stale.
- #399 `autopilot-issue-loop GH Actions failing — AUTOPILOT_GH_TOKEN expired` — open since 2026-07-09. 46 days. Nothing runs autonomously in CI until fixed.
- #394 `Fix brain-refresh[bot] credentials — 403 + SUPABASE_ACCESS_TOKEN missing` — open since 2026-07-05. 50 days. Brain sync broken.

**SECURITY — needs implementation:**
- #669 `[security] Class-wide: 95 routers missing Depends(block_demo_role) on mutating endpoints` — filed 2026-08-20, updated 2026-08-21. Labels: ai-ready, security. PR #653 has middleware proposal. Biggest open attack surface.
- #661 `security: scoring_config.py missing block_demo_role` — filed 2026-08-16. Subset of #669.
- #660 `fix(security): scoring_config.py missing block_demo_role on 4 mutating routes` — filed 2026-08-15, ai-ready. Same router, two separate issues filed — deduplicate.
- #643 `MEDIUM: appointment_briefs.py missing block_demo_role + plan gate + ai_usage_guard` — filed 2026-08-07, ai-ready. Pre-dates #669 sweep; covered by class fix.

**AUTOMATED / loop-health (no action needed, FYI):**
- #663 Agent OS loop health 2026-08-17
- #662 Agent OS loop health 2026-08-16
- #659 Agent OS loop health 2026-08-15

**DIGEST issues (open, stale — can close if no action taken):**
- #672 Morning digest 2026-08-21
- #670 Morning digest 2026-08-20
- #668 Morning digest 2026-08-19
- #667 Morning digest 2026-08-18
- #664 Morning digest 2026-08-17

Total open issues: 61.

---

## Open PRs — needing action

| # | Title | Age | Status |
|---|-------|-----|--------|
| #674 | subconscious: run #109 — Step 9J Dependabot auto-merge | 2d | DRAFT, updated today — review + merge |
| #653 | subconscious: runs 102-110 — Step 9J + GH #669 middleware proposal | 12d | DRAFT — contains block_demo_role middleware fix for #669 |
| #666 | bump @typescript-eslint/parser 8.64→8.67 | 7d | Ready, not draft — safe to merge |
| #665 | bump eslint 10.7→10.8.1 | 7d | Ready, not draft — safe to merge |
| #673 | ops: morning-digest 2026-08-21 | 3d | DRAFT — routine log, can merge or close |
| #671 | ops: morning-digest 2026-08-20 | 4d | DRAFT — routine log, can merge or close |
| #575 | Tenant-silence ops alert + Managed Agents Phase 0 prep | 32d | DRAFT — stale, review intent |
| #626 | subconscious: Step 9G v2 MCP primary KB autopopulate trigger | 22d | DRAFT — may be superseded by later runs |
| #648 | kb: drift sweep 2026-08-10 | 14d | DRAFT — needs review |
| #630 | bump vite 8.1.5→8.2.0 in /demo-platform | 21d | Ready, not draft — safe to merge |

---

## Subconscious Recommendation (2026-08-20 run)

**Step 9J: Dependabot auto-merge with major-version safety gate** — implemented in PR #674.
Previous run (2026-08-19) recommended Step 9I (block_demo_role class-sweep automation) → already filed as #669.
Both steps are in the proven SKILL.md channel. Step 9J closes the 4-week Dependabot backlog permanently.

---

## KB Log

Last successful compile: 2026-07-23 (8 articles, 114→124 total). No updates since.
Embeddings still deferred — VOYAGE_API_KEY not in cron env.
Root cause: secrets missing in GH Actions (same as #403). Fix #403 → unblocks KB pipeline.

---

## Top 3 Priorities Today

1. **Fix GH Actions secrets (#403, #399, #394)** — 50+ days stale. AUTOPILOT_GH_TOKEN + ANTHROPIC_API_KEY + SUPABASE_ACCESS_TOKEN. All require your action in repo Settings → Secrets. Nothing autonomous runs in CI until done. KB dead. Autopilot dead.

2. **Merge or action #669 class-wide security fix** — 95 routers unprotected. PR #653 has the middleware proposal. Either review + merge #653, or land the block_demo_role middleware patch directly. Close #660/#661 as duplicate of #669 once fixed.

3. **Merge ready Dependabot PRs (#665, #666, #630)** — non-draft, CI-green, safe. 7–21 days aging. PR #674 (Step 9J) adds auto-merge going forward; merge it too so future Dependabot PRs close themselves.
