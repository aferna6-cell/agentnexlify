# Improvement Backlog — 2026-05-23-pm (Run 32)

## Active

- **GH #181 Billing Fix** (Run 32 winner): Add `15000: "autopilot"` and `25000: "professional"` to billing.py AMOUNT_TO_PLAN. Replace two CI-blocking contradictory test methods. ~15 min. Moratorium-safe. Closes GH #181.
- **/moratorium-sprint** (Standing, runs 25–32): Invoke in any interactive session. Items A+B+D (~40 min). Draft PR. Pending 8→4→2 = moratorium exits. Tool ready: .claude/skills/moratorium-sprint/SKILL.md (7985fbb).

## Parking Lot (survived debate but not chosen)

- **dashboard_service.py + conversations_service.py coverage** (WEAKENED run 32): 2174732 created these two service files not confirmed in new test files. ROI: medium. Pre-condition: verify test_extracted_services.py coverage before recommending — see Questions for Next Run.
- **Pre-commit billing sentinel** (Bonus for GH #181 fix): Add Check 11 to pre-commit that validates AMOUNT_TO_PLAN has {9900,15000,25000,89900}. ~10 min. Implement alongside GH #181 fix. Prevents third AMOUNT_TO_PLAN regression.
- **Zapier plan_status enforcement** (GH #107, ROI 2.5): Security. Cancelled tenants bypass plan tier gate. Route via issue-to-pr-loop, NOT subconscious winner queue. Promote to first non-moratorium winner if #107 still open post-moratorium exit.
- **Fix email_sequences N+1 queries** (GH #112, ROI 2.3): 1001 queries per 1000 enrollments. Bulk .in_() fix. M-effort. Promote when email automation adoption grows or moratorium lifts.
- **Extract _process_pending_sends()** (GH #113, ROI 1.8): 120-line duplication in email_sequences.py. M-effort.
- **California AI Companion Disclosure Audit** (ROI 1.6): SB 243 + companion chatbot law in effect. Widget may require disclosure. Low-effort compliance review.
- **Bug-patterns.md split into monthly files** (ROI 1.8): 2320+ lines, growing unboundedly. Split + INDEX.md. Update auto-logger path.
- **Onboarding V2 characterization tests** (ROI 1.7): Write before first sprint issue. Covers POST /api/onboarding/start, complete_step, get_wizard_state.

## Rejected This Run

- **/moratorium-sprint as winner** (WEAKENED → standing action): 8+ consecutive recommendations without invocation. Bottleneck is commitment (40 min), not information. Winner slot better used for fresh, concrete improvement. Sprint remains standing highest-priority directive.
- **dashboard_service.py coverage as winner** (WEAKENED → parking lot): Evidence is speculative — test_extracted_services.py may already cover these services. Needs verification before promoting to winner.
- **Zapier plan_status as winner** (not debated — moratorium protocol): Issue tracked in GH #107, routed to issue-to-pr-loop per run 16 decision. Moratorium forbids.

## Questions for Next Run

1. Does `test_extracted_services.py` cover `dashboard_service.py` and `conversations_service.py`? Run `grep -n "dashboard_service\|conversations_service" /home/user/agentnexlify/tests/test_extracted_services.py` to confirm. If not: write smoke tests (3 function calls each with mocked Supabase). If yes: strike from parking lot.
2. Has GH #181 been implemented? Check `grep "15000\|25000" backend/routers/billing.py`. If yes: moratorium pending 8→7. If no: repeat winner.
3. Has any moratorium sprint item (A, B, or D) been completed? Check `grep -n "check_project_invariants" scripts/hooks/pre-commit` (Item A), `ls scripts/check-widget-sync.sh` (Item B), `ls .github/workflows/lead-qualifier-eval.yml` (Item D).
