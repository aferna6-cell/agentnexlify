# Nightly Commit Review — 2026-05-25

## Stats

- Review window: since last review commit `1553bf7` (2026-05-23 06:41 UTC) — 0 commits in strict 24h window, 3 commits in gap since last review
- Commits reviewed: 3
- LOW risk: 2
- MEDIUM risk: 1
- HIGH risk: 0
- Fixes applied: 0
- GH issues filed: 0 (existing GH #181 already tracks the only open finding)

---

## Commit Triage

| SHA | Message | Risk | Finding |
|-----|---------|------|---------|
| 14ac4d2 | subconscious: run 2026-05-23 (run 31) — Fix GH #181 AMOUNT_TO_PLAN + contradictory test | LOW | Docs/analysis only (subconscious state files). No code changes. |
| 2174732 | Refactor god classes: branding_service, control_center, channels_facebook, pipeline, social_media (#180) | MEDIUM | 31 files, 5038 ins / 2064 del. All checks pass — see detail below. |
| 21d66d7 | subconscious: run 2026-05-23-pm (run 32) — GH #181 billing fix with CI-trap evidence | LOW | Docs/analysis only (subconscious state files). No code changes. |

---

## Detailed Review: 2174732 — God-Class Refactor (#180)

### Critical invariants

| Check | Result |
|-------|--------|
| `from __future__ import annotations` in new FastAPI service files | **PASS** — none found across all 13 new service files |
| Bare `except:` blocks in new service files | **PASS** — none found |
| `leads` table uses `client_id` | **PASS** — `conversations_service.py:56`, `dashboard_service.py:61` correct |
| `conversations` table uses `client_id` | **PASS** — `conversations_service.py:78,151,163` correct |
| `chat_messages` table uses `tenant_id` | **PASS** — `conversations_service.py:26,133`, `dashboard_service.py:85` correct |
| `appointments` table uses `tenant_id` | **PASS** — `dashboard_service.py:115` correct |
| Other tables (`activity_log`, `faq_entries`, `website_content`, etc.) use `tenant_id` | **PASS** — verified in `dashboard_service.py` |

### Test coverage

135 new test functions across 5 new test files:
- `tests/test_extracted_services.py` — 29 tests
- `tests/test_facebook_oauth_webhook.py` — 40 tests
- `tests/test_pipeline_analytics.py` — 20 tests
- `tests/test_pipeline_presets.py` — 16 tests
- `tests/test_social_media_ai.py` — 30 tests

All 5 files live in `tests/` directory — covered by existing CI `python -m pytest tests` invocation (line 132 of `.github/workflows/pr-check.yml`). No CI wiring gap.

### auth.py

Went from 1601 → 1590 lines (duplicate handler removal). No `__future__` violations, no bare except blocks. Scope was narrowly correct: duplicate handlers removed, services extracted.

---

## Open Issues (carry-forward)

### GH #181 — billing: AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional

**Status**: Open. Last updated 2026-05-23.

**Subconscious evidence (runs 31+32)**: Both runs confirm the gap is still present and that `test_billing_amount_to_plan.py` lines 38-44 (`test_no_wrong_15000_mapping`, `test_no_wrong_25000_mapping`) block any correct fix from passing CI. GH #181 body already documents the CI trap and the exact fix required.

**Action required**: Human approval before touching billing code. Fix involves:
1. Add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/routers/billing.py:263`
2. Replace the two blocking test assertions (lines 38-44) with positive correctness assertions

No nightly agent should touch this — MEDIUM billing risk, explicit human approval required.

---

## Notes

- Three commits landed after previous review (2026-05-23 06:41 UTC) but before 2026-05-24 00:00 UTC. None landed in the 24h window ending 2026-05-25. Covered here to close the gap.
- No LOW-risk bugs found requiring immediate fix. Codebase clean on all critical invariants.
- Auth.py remains at 1590 lines — approaching god-class threshold (600+ for god class Rule 9, but auth.py is a routing file and has been this size intentionally). Worth a dedicated refactor sprint per #180 follow-up.
