# Run 50 — Improvement Backlog (2026-06-04-pm)

## Promoted to parking lot this run

### CI Fix: GH #185 — pyo3/cryptography failure
- **ROI:** HIGH (21 pytest failures, 10 days CI broken)
- **Effort:** ~5 min (1-line requirements.txt)
- **Fix:** `cryptography>=43.0.0,<44` in backend/requirements.txt
- **Timing:** After Idea 1 (em-dash AUTONOMOUS-EXECUTABLE) applies tonight
- **Notes:** Unblocks PR merge gates for all pending items. Additive, moratorium-safe.

---

## Standing items (unchanged from run 49)

### Item B — Widget 3-Copy Sync Guard (run 7/15, 40+ days)
- `scripts/check-widget-sync.sh` MISSING
- Wire into `scripts/hooks/pre-push`
- Fix CLAUDE.md Invariant #4 (2 → 3 widget copies)
- ~15 min human
- Note: widget copies currently in sync — no active harm from delay

### GH #181 — billing.py AMOUNT_TO_PLAN fix (critical_standing_action)
- Path confirmed: `backend/routers/billing.py:263`
- Add `{15000: 'autopilot', 25000: 'professional'}` to dict
- Update PR #183 (fix path references services/→routers/)
- ~15 min human
- Note: in rejected_paths as subconscious winner — critical_standing_action only

### email_sequences.py god-class split (run 41 active_direction)
- 1255L → email_crud + email_enrollment + email_processor
- Tools ready: god-class-splitter (e848b87), post-split-test-repair (d481799)
- ~2 hours human
- Prerequisite: GH #181 fix first
- Timing: after moratorium exit sprint

### AI-to-Human Handoff v1 (run 4, day 49+)
- Oldest pending item. Critical gap all 7 industries.
- Agent OS PR #188 merged — os_outbound_mirror.py handles SMS/email
- ~1 day implementation
- Timing: moratorium exit sprint

---

## Moratorium exit path (fastest route)
1. Tonight (2:37 AM): nightly applies em-dash patches (AUTONOMOUS-EXECUTABLE) → Check 10 wires
2. ~15 min: Item B widget sync guard (human)
3. ~15 min: GH #181 billing fix (human)
4. = ~3 closures in ~32 min → pending drops ~12 → moratorium exit review
