# Idea 4: VOYAGE_API_KEY Human-Action GH Issue

**Evidence:** Every recent KB compile log entry ends with "Embeddings SKIPPED (no credentials; FTS fallback covers retrieval)." The `knowledge-base/log.md` tail shows the 2026-07-23 run compiled 8 new articles but skipped embeddings due to missing VOYAGE_API_KEY. The `kb-autopopulate.yml` workflow (created run 82) requires VOYAGE_API_KEY as optional in GH Actions secrets — but it has never been set. With embeddings skipped: (a) semantic vector search is unavailable, (b) pgvector retrieval falls back to FTS-only, (c) when Step 9G triggers kb-autopopulate tonight, even if it succeeds, embeddings will still be skipped. GH #403 diagnostic comments from Step 9F/9G reference VOYAGE_API_KEY but don't create a standalone human-action issue for it.

**Action:** File GH issue via `mcp__github__issue_write`: title "VOYAGE_API_KEY missing from GH Actions secrets — KB embeddings skipped on every autopopulate run." Labels: `human-action-required`, `operational`. Body: (1) evidence — every compile since 2026-07-08 skips embeddings, (2) impact — semantic search degraded, AI widget chat uses FTS fallback only, (3) fix — add VOYAGE_API_KEY to GitHub repository secrets (Settings → Secrets → Actions), (4) confirm by checking next kb-autopopulate.yml run log for "Embeddings: N articles updated."

**Impact:** Once VOYAGE_API_KEY is set: future KB compiles (including Step 9G-triggered runs) refresh embeddings, restoring semantic vector search quality for tenant AI chat. FTS fallback is functional but less accurate for semantic queries ("do you have appointments this weekend?" vs. "booking availability").

**Category:** operational
