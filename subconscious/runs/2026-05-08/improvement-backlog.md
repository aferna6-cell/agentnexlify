# Improvement Backlog — 2026-05-08 (Run 15)

## Active
- **Widget 3-Copy Sync Guard** (run 7, 14 days pending): Create `scripts/check-widget-sync.sh`, wire into pre-push, fix CLAUDE.md Invariant #4. S-effort, 30 min. Moratorium mode winner.

## Bonus Steps (same sitting, 45 min total)
- **Wire check_project_invariants.py** (run 8, 13 days pending): Add Check 10 to `scripts/hooks/pre-commit`. 8 lines, 5 min. Drops pending 4→3.
- **Wire lead qualifier golden eval to CI** (run 14, 3 days pending): Create `.github/workflows/lead-qualifier-eval.yml`. Closes Issue #110. 20 min. Drops pending 3→2.
- **After all 3 bonuses**: pending = 1 (run 4 only). Moratorium fully exits.

## Urgent Escalation (pending 22+ days, human sprint required)
- **AI-to-Human Handoff v1** (run 4, 2026-04-16): Critical customer gap, all 7 industries, M-effort (1.5-2 days). Infrastructure exists. Explicit-trigger-only v1. MUST be planned in next sprint. After S-effort items clear the queue, this is the ONLY remaining item. No new subconscious winners should be accepted until this is implemented or explicitly rejected.

## Parking Lot (survived debate but not chosen this run)
- AI-to-Human Handoff v1 (run 4, urgent) — M-effort, cannot auto-implement; plan deliberately
- Fix email_sequences N+1 queries (GH #112, ROI 2.3) — promote when email automation grows
- Extract `_process_pending_sends()` from email_sequences.py (GH #113, ROI 1.8) — duplication
- California AI companion/chatbot disclosure audit (ROI 1.6) — SB 243 compliance
- Fix `agent-config-security.yml` windows-latest runner — trivial, bundle with next CI change
- Fix broken `[[claude-cowork]]` KB wikilink — create stub or remove; bundle with next KB compile
- Onboarding V2 characterization tests (ROI 1.7) — write before sprint issues ship
- widget_helpers Split Smoke Tests (ROI 2.0) — confirm implemented_unverified status
- Stripe Billing Smoke Tests (ROI 2.2) — revisit next pricing sprint
- Bug-patterns.md split by month (ROI 1.8) — 2320 lines, auto-logger writes to it

## Rejected This Run
- AI-to-Human Handoff as run 15 winner (moratorium re-triggered, but M-effort deadlock risk — more likely to stall for another 5+ runs than to get implemented; S-effort path clears queue faster)
- KB wikilink fix as winner (too low-leverage for moratorium priority slot)
- agent-config-security.yml runner fix as winner (cosmetic, trivial, bundle with other CI changes)

## Governance Corrections This Run
- **Moratorium re-triggered:** governance.json `moratorium_active` corrected to `true` (was stale `false`). Triggered at pending=4 > threshold=3 AND oldest=22 days > max_pending_age_days=14.
- **pending_approvals corrected to 4** (was 3 — run 14's recommendation wasn't counted in implementation_lag_warning).

## Questions for Next Run
1. Were any of the 3 S-effort bonus items implemented? If yes — which ones remain, and does pending ≤ 3?
2. Has run 4 (AI-to-Human Handoff) been scheduled for a sprint? If not, should it be explicitly rejected (which clears it from pending)?
3. `email_sequences.py` at 1255 lines (CRITICAL audit): is the N+1 fix (GH #112) being worked?
