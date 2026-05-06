# Improvement Backlog — 2026-05-06-pm (Run 15)

## Active (Run 15 Winner)
- **Wire check_project_invariants.py into pre-commit as Check 10** — 10-line bash block after Check 9 in `scripts/hooks/pre-commit`. All 6 invariant checks PASS. Closes run 8 (11 days pending). Drops queue 4→3. S-effort.

## Still Pending (awaiting human approval)
- **Wire golden eval harness to CI** (run 14, 2026-05-05) — 1 day. Create `.github/workflows/lead-qualifier-eval.yml`. Harness exists and passes locally. S-effort.
- **Widget 3-Copy Sync Guard** (run 7, 2026-04-24) — 12 days. `scripts/check-widget-sync.sh` never created. S-effort.
- **AI-to-Human Handoff v1** (run 4, 2026-04-16) — **20+ days. MORATORIUM WARNING.** Exceeds max_pending_age_days of 14. If pending at run 16 (30+ days), trigger dedicated escalation. Critical customer gap. M-effort.

## Security Escalation (Bypass Approval Queue)
- **Fix Zapier plan_status auth bypass (Issue #107)** — URGENT. Cancelled tenants can auth Zapier endpoints. S-effort. Action: grep for `_get_api_key_client` to confirm actual file path (bug-patterns.md path unconfirmed), then add plan_status filter + regression test. Use backend-dev agent directly, not subconscious approval queue.

## Parking Lot (survived debate but not chosen)
- **Fix N+1 in leads.py:714,866** (architecture audit, ROI ~2.0) — per-lead update in loop. 1158-line god class. Promote next sprint.
- **Fix email_sequences N+1 queries** (GH #112, ROI 2.3) — 1001 queries per 1000 enrollments. Promote when email adoption scales.
- **Extract _process_pending_sends()** (GH #113, ROI 1.8) — 120-line duplication in email_sequences.py. Promote when router hits 1500+ lines.
- **Onboarding V2 characterization tests** (ROI 1.7) — write before first sprint issue ships. Prevents `implemented_unverified` syndrome.
- **widget_helpers Split Smoke Tests** (ROI 2.0) — still deferred pending Playwright confirmation.
- **Fix KB broken wikilinks / orphaned articles** — 11 orphaned articles, 13 broken wikilinks. S-effort. Promote if KB query accuracy degrades.
- **California AI Companion/Chatbot Disclosure Audit** (ROI 1.6) — SB 243 in effect. Low-effort compliance check.
- **Stripe Billing Smoke Tests** (ROI 2.2) — promote next pricing sprint.

## Rejected This Run
- **AI-to-Human Handoff v1 (as run 15 winner)** — WEAKENED. No new evidence since run 4. M-effort. Moratorium just lifted 1 day prior. Escalated as moratorium warning instead.
- **Fix Zapier auth bypass (as run 15 winner)** — SURVIVES but escalated separately. Path unconfirmed. Security bug fix bypasses approval queue — wrong channel for subconscious winner.
- **Widget 3-Copy Sync Guard (as run 15 winner)** — SURVIVES but check_project_invariants closes run 8 (older pending). Widget sync is run 16 candidate.

## Governance Corrections This Run
- **Moratorium re-triggered:** pending went 3→4 when run 14 winner ("Wire golden eval harness to CI") was added. Queue now exceeds threshold of 3.
- **`implementation_lag_warning.runs_pending_approval` corrected:** was 3 in governance.json but actual count is 4 (runs 4, 7, 8, 14). Fixed in governance.json this run.

## Questions for Next Run (Run 16)
1. Was Check 10 (check_project_invariants) added to pre-commit? Run 8 closed?
2. Was `.github/workflows/lead-qualifier-eval.yml` created? Run 14 closed?
3. Was the Zapier auth bypass confirmed and fixed (Issue #107)?
4. Widget 3-Copy Sync Guard (run 7) — `scripts/check-widget-sync.sh` created?
5. AI-to-Human Handoff (run 4) — days pending? If 30+, mandate escalation as sole recommendation.
6. Was the leads.py N+1 (lines 714, 866) addressed as part of any sprint work?
