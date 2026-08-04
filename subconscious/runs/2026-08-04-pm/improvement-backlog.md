# Improvement Backlog — 2026-08-04-pm (Run 101)

## Active
- **Strengthen SKILL.md dedup guard** — Replace prose-only Phase 8 guard in `.claude/skills/subconscious/SKILL.md` with mandatory STEP 0 tool-call pre-flight (`mcp__github__list_pull_requests`). Commits artifacts to existing open subconscious PR branch instead of creating duplicates.

## Parking Lot (survived debate but not chosen)

- **Resolve #625 vs #626 Step 9G competition** — Human action: review both PRs, merge the one matching `subconscious/runs/2026-07-23/winning-concept.md` implementation sketch exactly, close the other as duplicate. KB currently 12 days stale. Step 9G repairs it within hours of merge. This is a human-action item, not an autonomous winner.

- **VOYAGE_API_KEY alert (Step 9J)** — After Step 9G merges: add Step 9J bash block to nightly SKILL.md that detects "SKIPPED" or "no credentials" in `knowledge-base/log.md` and comments on GH #403 with diagnostic. Currently VOYAGE_API_KEY missing → embeddings silently degraded to FTS-only for all 3 live tenants.

- **Consolidate stale subconscious PRs** — Human action: close clearly superseded drafts (#606 feature-docs-trio, #611 Step 9H GH Actions alerter [Step 9H was killed in run 100 — MCP tenant count too low], #613 Step 9I). Keep #625 or #626 (whichever is merged). Target: ≤1 open subconscious PR after cleanup.

- **Agent OS loop-health noise reduction** — Re-evaluate after Agent OS scales to 5+ tenants. At current scale (2-3 tenants), loop-health issues are expected to be sparse.

## Rejected This Run

- **Typed KB notes retrieval audit** — WEAKENED (not chosen as winner; promoted to run_102_mandate item 2). Not killed — XS effort retrieval audit definitively answers whether typed notes surface in AI chat responses. Demoted from winner slot because dedup guard is more structurally impactful.

## Questions for Next Run (Run 102)

1. Did the dedup guard STEP 0 take effect? Does `grep "STEP 0" .claude/skills/subconscious/SKILL.md` return a match? (Should: if this run's artifact was committed to #625 or #626 and merged)
2. Were #625/#626 resolved? How many open subconscious PRs remain?
3. Does typed KB notes retrieval path filter by `source`? Grep result from run_102_mandate item 2.
4. Is VOYAGE_API_KEY still missing? `knowledge-base/log.md` last entry still shows "SKIPPED"?
5. First Agent OS tenant: any new tenants onboarded since 2026-07-23 (3 total at last check)?
