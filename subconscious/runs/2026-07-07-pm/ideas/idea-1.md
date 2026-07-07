# Idea 1: Migrate KB Autopopulate from Local Cron to GitHub Actions

**Evidence:** `knowledge-base/log.md` last entry: 2026-05-05 (63 days ago). `scripts/daily/kb-autopopulate.sh` line 7-8: "Cron (installed by scripts/daily/setup-cron.sh): `0 6,18 * * * cd /home/aidan/agentnexlify && bash scripts/daily/kb-autopopulate.sh`". No KB autopopulate workflow in `.github/workflows/` (confirmed by listing — only `refresh-brain.yml` exists for automation). Script fails if `AGENTNEXLIFY_CLAUDE_BIN` or `claude` CLI not in PATH — both unavailable in CI/remote environments. run_82_mandate explicitly designates this as PRIMARY candidate.

**Action:** Write `.github/workflows/kb-autopopulate.yml` — scheduled `0 6,18 * * *` UTC, uses `claude` CLI via `npx @anthropic-ai/claude-code@latest --print` (headless mode), passes `ANTHROPIC_API_KEY` + `VOYAGE_API_KEY` from repository secrets, mirrors the headless prompt in the current script. Local cron remains as fallback but GH Actions becomes the canonical trigger.

**Impact:** Restores KB to twice-daily growth. Removes dependency on developer's local machine being online. Knowledge base compounds again after 63-day stall. Subconscious runs on current market + product intelligence rather than May 2026 snapshots. ~110 → 140+ articles when catch-up runs complete.

**Category:** operational

**Confidence pre-debate:** HIGH — root cause clear (local cron can't run in ephemeral/remote env), fix path clear (GH Actions workflow pattern already proven by refresh-brain.yml), impact high and measurable.
