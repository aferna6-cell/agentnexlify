# Improvement Backlog — 2026-06-18-pm

## Active

- Fix GH #308: add `delete_key()` to idempotency.py + call in stripe_webhooks.py exception handler + regression test (payment revenue bug, moratorium override, nightly review path)

## Parking Lot (survived debate, not chosen this run)

- **Fix GH #292/#293** — add `chatbot`/`agent_os` to `sms_rate_limiter._UNLIMITED_PLANS` + `api_key_auth._ALLOWED_PLANS` + billing_reconciliation caps. All new paid tenants get wrong SMS limits and can't use Zapier. S-effort ~10 min. Bonus A in winning-concept.md. Product decision: chatbot=200/day, agent_os=500/day.
- **Plan-name invariant guard (check 7)** — add to `check_project_invariants.py`: scan for `chatbot`/`agent_os` in 3 files. AUTONOMOUS-EXECUTABLE. Must sequence AFTER GH #292/#293 fix. Bonus B in winning-concept.md.
- **Leadgen → CRM import path** — `scripts/leadgen/merge_leads.py` produces Instantly-ready CSV but no path into AgentNexLiFy leads table. Medium effort. Premature until pipeline proven in production.
- **Home.jsx god-class split (1006L)** — new features landing in it daily. Split into HeroSection, LeadCaptureSection, TestimonialsSection under `frontend/src/pages/home/`. Human-required, M-effort.
- **email_sequences.py split (1143L)** — run 41 winner, still pending. Down from 1255L. Three clean concerns (CRUD/enrollment/processor). god-class-splitter SKILL.md ready. GH #292/#293 prerequisite resolved.

## Rejected This Run

- None new (carried ideas into parking lot or bonus)

## Governance Corrections Applied This Run

- Runs 30, 31, 32, 34, 51 (AMOUNT_TO_PLAN old-billing fixes): marked **moot** — billing repriced to 2-plan model ($19.99 chatbot / $99.99 agent_os), AMOUNT_TO_PLAN confirmed updated in billing.py.
- PR #183 (run 51 pending): **moot** — targeted old AMOUNT_TO_PLAN dict, now superseded by 2-plan repricing.

## Questions for Next Run

1. Was GH #308 implemented by nightly review or interactive session? Check `stripe_webhooks.py:105` for `await delete_key()` and `idempotency.py` for `delete_key` method.
2. Were Bonus A (GH #292/#293) and Bonus B (check 7) implemented? Check `sms_rate_limiter.py:10` for `chatbot`/`agent_os` and `check_project_invariants.py` for check 7.
3. Is Home.jsx still 1006L or growing? Does a split plan exist?
4. Was the leadgen pipeline used for actual outreach? Any leads imported to AgentNexLiFy?
