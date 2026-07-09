# Winning Concept — 2026-07-07-pm (Run 82)

## Recommendation
Create `.github/workflows/kb-autopopulate.yml` — a GitHub Actions scheduled workflow that runs the KB auto-populate cycle twice daily, eliminating the 63-day silent failure caused by local cron dependency.

## Why This, Why Now
`knowledge-base/log.md` shows the last successful KB autopopulate was 2026-05-05 — 63 days ago. The script (`scripts/daily/kb-autopopulate.sh`) is a LOCAL cron job requiring the `claude` CLI at `/home/aidan/...`, a path unavailable in CI/remote environments. No GitHub Actions workflow for KB exists (confirmed: `.github/workflows/` has `refresh-brain.yml` but no KB equivalent). The `refresh-brain.yml` workflow proves the GH Actions pattern works for this codebase. KB feeds the widget's AI responses, subconscious evidence quality, and competitive intelligence — 63 days stale means the platform's knowledge layer is running on May 2026 data while GoHighLevel, Drillbit, and Phonely have all shipped new features. The run_82_mandate named this as the PRIMARY candidate.

## Implementation Sketch

1. **Create `.github/workflows/kb-autopopulate.yml`:**
   - Schedule: `cron: '0 6,18 * * *'` (6 AM + 6 PM UTC, matching local cron intent)
   - Runner: `ubuntu-latest`
   - Steps:
     a. `actions/checkout@v4` with `token: ${{ secrets.GITHUB_TOKEN }}`
     b. `actions/setup-node@v4` with node 20
     c. `npm install -g @anthropic-ai/claude-code` (or pin: `@2.1.98` per claude-version-pin.md)
     d. Run headless discover: `claude --print "$DISCOVER_PROMPT"` using the same prompt body from `scripts/daily/kb-autopopulate.sh` lines ~50-90
     e. Run headless compile: `claude --print "$COMPILE_PROMPT"` using prompt body from script lines ~110-140
     f. `git config + git add knowledge-base/ + git commit --allow-empty-message + git push` (matches pattern in `refresh-brain.yml`)
   - Env secrets needed: `ANTHROPIC_API_KEY` (required), `VOYAGE_API_KEY` (optional — embeddings; graceful-skip if absent), `SUPABASE_ACCESS_TOKEN` (optional — pgvector upsert; graceful-skip if absent per existing log behavior)

2. **Sequence note:** `VOYAGE_API_KEY` and `SUPABASE_ACCESS_TOKEN` should be added to GitHub repo secrets. `SUPABASE_ACCESS_TOKEN` is already the blocker for brain connectors (GH #394 / run 79 pending human action) — resolving that unblocks both brain connectors AND the KB pgvector upsert in one action.

3. **Do NOT delete the local cron.** Keep `scripts/daily/kb-autopopulate.sh` + cron setup as local fallback. GH Actions becomes canonical trigger; local cron is override when working offline.

4. **Verify:** After merging, check `Actions` tab for the next 6 AM or 6 PM UTC run. Confirm `knowledge-base/log.md` gets a new entry. Confirm `knowledge-base/wiki/` gets new articles.

5. **On success:** Update `subconscious/state/governance.json` active_directions entry to `status: "implemented"`.

## What This Replaces
Run 81 winner was: Add `ai-ready` label to GH #385 (SMS Compliance Dashboard). That item is now `status: pending_autonomous` — label addition pending tonight's nightly (460ea68 ran BEFORE run 81 committed; label will be applied by 2026-07-08's nightly). This run does not replace that direction — it adds a new active direction alongside it.

## Confidence
**HIGH** — root cause is confirmed (local cron path, no GH Actions workflow), fix is proven pattern (`refresh-brain.yml`), impact is measurable (KB article count), mandate explicitly designated this as primary target.

## Autonomous Executable?
**YES** — writing a new GitHub Actions workflow file is zero-risk, additive, reversible. No schema changes, no auth changes, no existing code modified. Nightly can execute this without human approval. Mark: `autonomous_executable: true`.
