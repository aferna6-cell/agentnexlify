# Improvement Backlog — Run 2026-07-19

## Winner

**Step 9F: KB Autopopulate Staleness Check — channel pivot to human-session direct edit**
- Category: workflow
- Effort: XS
- Target file: `.claude/skills/nightly-commit-review/SKILL.md`
- Action: Insert 28-line bash block after Step 9E (lines 265-288)
- Full block: `subconscious/runs/2026-07-17-pm/winning-concept.md` (exact text, verbatim)
- Run 100 check: `grep -c "Step 9F" .claude/skills/nightly-commit-review/SKILL.md` — must return ≥1

## Supporting Recommendations

### A. conversation_enrichment_job.py Scheduling (operational, S)
Read `backend/services/automation/scheduled/conversation_enrichment_job.py` — confirm WHERE clause, rate controls, idempotency. Then add to `backend/services/automation/scheduled_jobs.py` following the `auto_complete_past_appointments` pattern (lines 34, 62). File GH issue with implementation review notes before scheduling.

### B. GH #413 Final Escalation (customer_value, XS)
Post comment on GH #413 framing REFERRAL_REWARD_ENABLED=1 in terms of appointment-completion: PR #475 is live, first appointments are auto-completing, first review requests are imminent. Setting REFERRAL_REWARD_ENABLED=1 before first completion bundles referral reward with first review request — highest-leverage moment. Day 29+, 7 prior comments with no human response.

### C. kb_hybrid Enable for Keys Koffee (customer_value, XS)
In a human-interactive session with Supabase MCP: `INSERT INTO platform_settings (tenant_id, key, value) VALUES ('<keys_koffee_tenant_id>', 'kb_hybrid_enabled', '1');` — enables BM25+pgvector hybrid retrieval for Keys Koffee. No code deployment. Reversible (DELETE row to revert).

## Parking Lot

| Item | Reason | Revisit |
|------|---------|---------|
| platform_flags ALLOWED_TOGGLE_KEYS guard | Nightly said "no action required"; 0 present-risk rows; maintenance cost | After first misconfigured row incident |
| kb_hybrid_retrieval broader rollout | Needs settings UI or per-tenant toggle discovery | After platform_flags UI + GH #399 resolved |
| conversation_enrichment scheduling | Read-before-schedule gate required | After GH issue review |
| BotHealthPage.jsx improvements | Shipped PR #475 — baseline exists, iterate when needed | Post-GH #399 |
| appointment_completion edge cases | Shipped as appointment_jobs.py PR #475 — monitor for edge cases | Post-monitoring period |

## Governance Corrections

Three items previously tracked as pending/parking-lot are IMPLEMENTED by PR #475 (commit 23b1da5, 2026-07-19):

1. **appointment_completion.py** → implemented as `backend/services/automation/scheduled/appointment_jobs.py`. `auto_complete_past_appointments()` wired in `scheduled_jobs.py` lines 34+62. GH #454 CLOSED.
2. **BotHealthPage.jsx** → implemented in `frontend/src/pages/BotHealthPage.jsx`. GH #465 CLOSED.
3. **AttributionPage.jsx / Lead Source Analytics** → implemented in `frontend/src/pages/AttributionPage.jsx`. GH #453 CLOSED. (Long-standing parking-lot item from run 85; active_direction `status: pending_autonomous` should be updated to `implemented`.)
