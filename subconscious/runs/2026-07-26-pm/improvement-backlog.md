# Improvement Backlog — 2026-07-26-pm (Run 104)

## Active
- Step 9H: GH Actions spending-limit daily heartbeat — IMPLEMENTED (run 104, 2026-07-26-pm). Fires each nightly when ≥4/5 recent runs failed; pings GH #500 with dated status; self-silences when #500 closed. Ships with Step 9G in PR #577.

## Parking Lot (survived debate but not chosen)
- **Managed Agents Phase 0 GH issue** — Run 103 carry-forward. Issue template:
  - Title: `[Managed Agents] Phase 0: provision environment + Railway env vars + smoke test`
  - Checklist: (1) Anthropic console → Managed Agents → Create Environment → note ID. (2) Note LEAD_QUALIFIER_AGENT_ID from console. (3) Set both in Railway env vars. (4) Redeploy. (5) `GET /api/managed-agents/health` → expect `{"status": "active"}`. (6) E2E: POST lead to qualify endpoint.
  - Requires human approval to create issue (governance: pending_approval)
- **PR #577 merge readiness note** — Add "CI failure is GH #500, not this PR" explicit note to PR body. Bonus action post-commit.
- **email_sequences auth failures (8)** — pre-existing inherited from split, not regressions. Create GH issue when CI returns. Label: test-debt, ai-ready.
- **KB local fallback in Step 9G** — When `gh workflow run` fails (Actions down), try `bash scripts/daily/kb-autopopulate.sh` as fallback. Deferred: needs env var verification.
- **Step 9I: VOYAGE_API_KEY rotation schedule** — Track VOYAGE_API_KEY expiry in nightly. Park until Step 9H proves the pattern.

## Rejected This Run
- None new — all ideas survived debate or were parking-lot'd.

## Questions for Next Run (Run 105)
1. Did Step 9H fire? Check nightly-2026-07-27 for "Step 9H:" line.
2. GH #500 resolved? Any successful Actions run since 2026-07-26?
3. PR #577 merged? (Step 9G + 9H on main?)
4. AUTOPILOT_GH_TOKEN rotated (GH #399)?
5. Managed Agents Phase 0 approved by owner? GH issue created?
