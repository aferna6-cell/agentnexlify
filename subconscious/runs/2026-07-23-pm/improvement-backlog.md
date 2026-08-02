# Improvement Backlog — Run 101 (2026-07-23-pm)

## Active (recommended, pending human approval)

### Step 9G: KB Autopopulate Self-Healing Trigger
- **What:** Add Step 9G bash block to `.claude/skills/nightly-commit-review/SKILL.md` — trigger `gh workflow run kb-autopopulate.yml`, check status after 30s, comment on GH #403 with specific failure diagnostic if workflow fails.
- **Why:** Step 9F fires but doesn't heal. Automated workflow broken (missing secrets). 2nd carry-forward cycle.
- **Category:** workflow_efficiency
- **Effort:** XS (~30 bash lines)
- **Approved by human:** PENDING

---

## Parking Lot (investigate, not yet recommended)

### SHOW_BOOKING_PANEL Funnel Completeness (run 102)
- **What:** Verify `widget_chat_booking_action.py` is registered in `main.py` and `show_booking_flag` consumed by the frontend widget to trigger booking panel.
- **Why:** 19 new lines in bug-patterns.md on e9b4972 is a yellow flag on a revenue-critical path.
- **Next trigger:** check if any 404 or unhandled flag errors appear in nightly reviews.
- **Category:** code_health

### Credential Tracking: VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN
- **What:** Add both to `ops/credential-rotation-schedule.md` with status "not_set — required for kb-autopopulate.yml".
- **Why:** Step 9E only checks listed credentials. Missing entries never surface.
- **Note:** Lower leverage than Step 9G. Will be moot once secrets are set.
- **Category:** operational

### email_sequences.py Split Registration
- **What:** Confirm email_crud, email_enrollment, email_processor are all imported + registered in main.py.
- **Why:** Past god-class splits required main.py registration fixes.
- **Status:** Likely already correct (commit ab1a7c2 was thorough). Verify on next nightly.
- **Category:** code_health

---

## Rejected / Frozen

### AI Human Handoff (FROZEN — rejected 3+ times)
- **Reason:** Proposed and rejected across runs 47, 62, 78. Frozen per governance. Do not propose again.

### Voice Workforce Bridge Monitoring
- **Why rejected:** Insufficient failure evidence. Speculative. No errors in nightly reviews.

---

## Open Questions

1. When will human set ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN in GH Actions secrets? (GH #403 open, no human response in 10+ days)
2. Is SHOW_BOOKING_PANEL wired end-to-end? (needs investigation — not confirmed broken)
3. Will Agent OS tenant count reach >5 to trigger LoopHealthPage promotion? (currently 2-3)
