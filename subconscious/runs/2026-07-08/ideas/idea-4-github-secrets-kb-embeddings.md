# Idea 4 — Add SUPABASE_ACCESS_TOKEN + VOYAGE_API_KEY to GitHub Repo Secrets

**Category:** operational
**Effort:** XS (2 min in GitHub Settings → Secrets)
**Confidence:** HIGH

## What
The new `kb-autopopulate.yml` workflow has SUPABASE_ACCESS_TOKEN and VOYAGE_API_KEY as optional secrets with graceful-skip behavior. Without them, articles compile to `knowledge-base/wiki/` but pgvector embeddings are never upserted. This means semantic search (`/kb-query`) never gets new data even after the workflow fires.

## Evidence
- `knowledge-base/log.md` [2026-05-05]: "Supabase MCP unauthorized" appears in cron output — embeddings have been failing since at least 2026-05-05
- kb-autopopulate.yml created by f958ab7 explicitly marks these as optional/graceful-skip
- Run 82 winning-concept.md §Implementation Sketch: "SUPABASE_ACCESS_TOKEN is already the blocker for brain connectors (GH #394 / run 79 pending human action) — resolving that unblocks both brain connectors AND the KB pgvector upsert in one action"
- If GH #394 human action (run 79 pending_human) is taken, SUPABASE_ACCESS_TOKEN is already set for brain connectors. Setting it in GH repo secrets is an additional 1-min step.
- VOYAGE_API_KEY enables higher-quality embeddings. Optional but recommended.

## Relationship to Run 79 Pending_Human
Run 79 asks human to: (1) rotate GitHub token, (2) set SUPABASE_ACCESS_TOKEN in cron env. If (2) is done, adding the same token to GitHub repo secrets costs 0 additional effort.

## Autonomous-Executable?
NO — secrets require human access to GitHub repo Settings → Secrets.

## Implementation Sketch
1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Add `SUPABASE_ACCESS_TOKEN` (same value as cron env)
3. Add `VOYAGE_API_KEY` (Voyage AI API key — obtain from voyage.ai)
4. Workflow will pick them up on next cron run automatically
