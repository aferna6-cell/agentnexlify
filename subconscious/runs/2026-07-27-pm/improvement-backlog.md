# Run 106 Improvement Backlog — 2026-07-27-pm

## Parking Lot (new additions this run)

### feature-docs-trio skill (1st appearance as parking lot candidate)
**Promote condition:** Run 107, if still unimplemented
**Evidence:** 3 occurrences in 7 days (commits 717c7f3, 14ebe8e, d50d1e8). Pattern: KB wiki article + ADR entry + INDEX.md update + optional runbook, each within 2 days of feature PR merging. 30-45 min saved per feature shipped.
**Weakness:** invoke gap — feature-build SKILL.md has no documentation step. Must create skill THEN add reference to feature-build. Both steps required in sequence.
**Effort:** S (create skill file + update feature-build reference)

### email_sequences Authentication Failures GH issue (8 edge cases)
**Promote condition:** GH #500 resolved and CI returns
**Evidence:** email_sequences.py god-class split (2026-07-23) exposed auth failure edge cases visible in logs. Filing GH issue with ai-ready label queues it for issue-to-pr-loop.
**Weakness:** filing now queues it but implementation blocked until GH #500 fixed. CI dark means no validation.
**Effort:** XS (file issue) + M (fix)

### VOYAGE_API_KEY Rotation Schedule Entry (Step 9I)
**Promote condition:** when VOYAGE_API_KEY actually set in prod
**Evidence:** KB embeddings absent (skipped 2026-07-23 catch-up due to absent VOYAGE_API_KEY). credential-rotation-schedule.md exists (Step 9E, run 84). Adding VOYAGE_API_KEY row prevents future silent embedding gap.
**Weakness:** documentation-only; no urgency signal while key absent.
**Effort:** XS

## Standing Carry-Forward Items (from prior runs)

| Item | Status | Source |
|------|--------|--------|
| PR #577 merge | Open/draft 4 days | Step 9G + 9H on branch awaiting merge |
| GH #500 Actions billing | Open day 7 | 4-step checklist posted run 101 |
| GH #399 AUTOPILOT_GH_TOKEN | Expired | 30 ai-ready issues blocked |
| Managed Agents Phase 0 | Pending human approval | Run 103 winner |
| LoopHealthPage.jsx | Deferred | Promote when Agent OS >5 tenants |
| MCP quickstart doc | Deferred | Promote when 2nd MCP tenant activated |
| conversation_enrichment_job.py scheduling | Blocked | GH #399 stalls queue |
| kb_hybrid retrieval enable | Blocked | GH #399 or settings UI needed |

## Run 107 Mandate

1. god-class-splitter Step 7 fix confirmed in SKILL.md? (`grep -c "backward-compat" .claude/skills/god-class-splitter/SKILL.md` — MUST PASS)
2. PR #577 merged? If yes: confirm Step 9G + 9H on main branch.
3. Step 9H fired on nightly-2026-07-28? Check nightly log for 'Step 9H:' line.
4. GH #500 resolved? Any successful Actions run?
5. Managed Agents Phase 0 GH issue approved by owner?
6. GH #399 AUTOPILOT_GH_TOKEN rotated?
7. feature-docs-trio: still no skill file? Promote to run 107 winner if unimplemented (1st-cycle carry-forward condition).
