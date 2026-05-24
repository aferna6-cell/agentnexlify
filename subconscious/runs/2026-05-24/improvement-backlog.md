# Improvement Backlog — 2026-05-24 (Run 33)

## Active

- **GH #181 Billing Fix** (Run 33 winner, third rec): Add `15000: "autopilot"` and `25000: "professional"` to billing.py AMOUNT_TO_PLAN. Remove two CI-blocking contradictory test methods. ~15 min. Moratorium-safe. Closes GH #181. Bonus: Check 11 pre-commit sentinel + CLAUDE.md note (both ~5-10 min each, add alongside).
- **/moratorium-sprint** (Standing, runs 25–33): Invoke in any interactive session. Items A+B+D (~40 min). Draft PR. Pending 9→5→2 = moratorium exits. Tool ready: .claude/skills/moratorium-sprint/SKILL.md (7985fbb). **This is the highest-leverage single interactive action.**

## Parking Lot (survived debate but not chosen)

- **faq_service.py + industry_faqs.py smoke tests** (WEAKENED run 33, new from 2174732): industry_faqs.py (415L) and faq_service.py (74L) have no confirmed test coverage after the god-class refactor. Pre-condition: read both files to confirm function-logic content vs static data. If logic-heavy: run 34 winner candidate. ROI: medium-high if logic-heavy, low if static.
- **widget_config_service.py smoke test** (not debated, new from 2174732): 62-line widget-critical service with no test coverage. 3-5 smoke tests in test_extracted_services.py. ~15 min, moratorium-safe.
- **Zapier plan_status enforcement** (GH #107, ROI 2.5): Cancelled tenants bypass plan tier gate. Route via issue-to-pr-loop, NOT subconscious winner queue. Promote to first non-moratorium winner if #107 still open post-moratorium exit.
- **Fix email_sequences N+1 queries** (GH #112, ROI 2.3): 1001 queries per 1000 enrollments. Bulk .in_() fix. M-effort. Promote when email automation adoption grows or moratorium lifts.
- **Extract _process_pending_sends()** (GH #113, ROI 1.8): 120-line duplication. M-effort.
- **California AI Companion Disclosure Audit** (ROI 1.6): SB 243 + companion chatbot law in effect. Low-effort compliance review.
- **Bug-patterns.md split by month** (ROI 1.8): 2320+ lines unbounded. Split + INDEX.md.
- **Onboarding V2 characterization tests** (ROI 1.7): backend/tests/test_onboarding_characterization.py before sprint issue 1.

## Removed from Parking Lot This Run

- **dashboard_service.py + conversations_service.py coverage** (run 32 question answered): test_extracted_services.py confirmed to have 26 matches for both services, multiple test functions. Coverage exists. STRIKE from parking lot.

## Rejected This Run

- **/moratorium-sprint as winner** (WEAKENED → standing action): Ninth consecutive recommendation without invocation. Bottleneck is commitment (40 min), not information. Winner slot goes to shorter-commitment item. Sprint remains standing highest-priority directive; does not need to hold winner slot to be actionable.
- **faq_service + industry_faqs as winner** (WEAKENED → parking lot): Evidence is inferred (file size) not confirmed (file content). Needs content verification before promoting. Lower urgency than CI-trap billing fix.

## Governance Actions Applied This Run

- **Run 32 questions answered**: dashboard_service + conversations_service coverage confirmed (26 matches in test_extracted_services.py). Strike from parking lot. GH #181 still open. Sprint items A/B/D still MISSING.
- **Moratorium day**: 19+ (since 72f8204 May 5).
- **True pending count**: 9 after run 33 (runs 4, 20, 21, 28, 29, 30, 31, 32, 33). After /moratorium-sprint + governance audit: 9→5→2 = moratorium exits.

## Questions for Next Run

1. Has GH #181 been implemented? Run `grep "15000\|25000" backend/routers/billing.py | grep -v "legacy"`. If yes: pending 9→8. If no: confirm winner again only if CI trap is still active.
2. Has any sprint item (A, B, D) been completed? Check: `grep -n "check_project_invariants" scripts/hooks/pre-commit` (Item A), `ls scripts/check-widget-sync.sh` (Item B), `ls .github/workflows/lead-qualifier-eval.yml` (Item D).
3. What is in faq_service.py and industry_faqs.py — function logic or static data? Run `wc -l backend/services/faq_service.py backend/services/industry_faqs.py` and read first 30 lines of each. If logic-heavy: promote to run 34 winner.
4. Has the 2174732 god-class refactor introduced any runtime errors in production (Railway logs)?
