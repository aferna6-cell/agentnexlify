# Improvement Backlog — 2026-08-22

## Active
- **Step 9J: Dependabot auto-merge in nightly SKILL.md** — IMPLEMENTED this run (1st carry-forward mandate). Next nightly will merge CI-green Dependabot PRs automatically. Check nightly-2026-08-23 for "Step 9J:" log line.

## Parking Lot (survived debate, not chosen this run)
- **Step 9K: Stale autonomy PR closer** — Named in run_109_mandate as candidate. 4-5 subconscious draft PRs aging from runs 102-108. Add Step 9K to SKILL.md: list PRs with head branch "subconscious", close drafts >14 days with no review comments, post comment linking latest winning-concept.md. Run 110 candidate.
- **KB autopopulate direct-compile fallback** — KB 30d stale, GH Actions blocked on ANTHROPIC_API_KEY. Before proposing Step 9H, verify: does the nightly Claude Code session have ANTHROPIC_API_KEY available as env var? Check `.env` or Railway env visibility. Run 110 investigation item.

## Rejected This Run
- **GH #669 middleware spec comment** — One-off GH comment, not structural SKILL.md improvement. Human should drive middleware vs per-route architectural decision once GH #399 resolves.
- **Step 9L (GH #399 age-pressure in nightly report)** — 4+ prior manual comments had zero effect. Morning digest already surfaces GH #399 status. Marginal value; risk of noise. Revisit if GH #399 still open at run 111.

## Questions for Next Run
1. Did nightly-2026-08-23 log "Step 9J:" line? How many Dependabot PRs merged?
2. Open subconscious PRs: verify count via mcp__github__list_pull_requests (head branch "subconscious"). If ≥3, implement Step 9K directly.
3. Is ANTHROPIC_API_KEY available in nightly Claude Code session env? Check before proposing KB direct-compile fallback.
4. GH #399: still open Day 42+? If yes: is there a new escalation path beyond GH comments (e.g., email to owner)?
5. GH #669: any PR opened since 2026-08-20 for middleware-level block_demo_role?
