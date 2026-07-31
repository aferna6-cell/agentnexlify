# Improvement Backlog — 2026-07-31-pm (Run 102)

## Active
- **Step 9I: GH #500 spending limit nightly escalation** — add bash block to SKILL.md after Step 9G. Daily comment on #500 when no workflows active in 24h, naming Step 9G blockage + KB staleness + 3 tenant AI chat impact.

## Parking Lot (survived debate but not chosen)

- **INTEGRATIONS_ENC_KEY nightly escalation on GH #536** (Day 10, migration 176 blocked). WEAKENED in debate: valid but lower urgency than Idea 1. Step count in SKILL.md growing; fold into Step 9E's infra-blocker scope or promote as standalone when #536 passes Day 14. Revisit run 103 if spending limit resolves this week.
- **VOYAGE_API_KEY human-action GH issue** — file issue naming missing secret, exact fix (GitHub Settings → Secrets → Actions → VOYAGE_API_KEY). KB embeddings have been SKIPPED on every compile since at least 2026-07-08. Semantic search degraded (FTS fallback active). File as bonus action during this run if time permits.

## Rejected This Run
- **Step 9J — Nightly Autonomy Sweeper**: KILLED. Below Day 7+ mandate threshold (Day 3 from 2026-07-28 ship). Zero confirmed stranded runs. Execution environment compatibility unverified (nightly context vs. CLI). Revisit 2026-08-04 (Day 7) if evidence of stranded runs exists.
- **MCP tenant monitoring (Step 9H)**: Still in rejected_paths from run 100. MCP tenant count still 1. Revisit when >5.

## Questions for Next Run (Run 103)
1. Did Step 9I fire tonight (nightly 2026-07-31 or 2026-08-01)? Check nightly log for "Step 9I:" line.
2. Did Step 9G fire tonight? Exit code 0 (success) or non-zero (spending limit blocked)? Check nightly log for "Step 9G:" line.
3. If Step 9G succeeded: did kb-autopopulate.yml complete? Check knowledge-base/log.md for entry dated 2026-08-01 or later.
4. If Step 9G failed due to spending limit: does GH #500 have Step 9G diagnostic in comments? Does GH #403 have Step 9G failure comment?
5. GH Actions spending limit (GH #500) — has billing cycle reset or limit been increased by run 103? Check `gh run list --limit=5`.
6. Autonomy sweeper Day 7 (2026-08-04): has any stranded run appeared since 2026-07-28 ship date? Promote Step 9J if evidence exists.
7. VOYAGE_API_KEY: was the GH issue filed (bonus action)? Has the human actioned it?
