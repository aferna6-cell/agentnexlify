# Idea 1 — Write Referral Grant Resend Email Notification

## Category
customer_value

## Effort
S (30 min estimate per run 92 comment)

## Evidence
- GH #413 run 92 comment (2026-07-13): explicitly stated "Email notification ships in a follow-up sprint — 30 min to wire a Resend transactional email once activation proves the flow works end-to-end."
- 4 consecutive autonomous comments on GH #413 (runs 89-92) = 0 human responses
- referral_reward.py:212-225 (`_grant_sync()`) fires Stripe balance transaction silently — no email sent to referrer
- 5 test files exist for the referral system (runs 90-91 confirmed)
- REFERRAL_REWARD_ENABLED=1 not set (safe to ship gated code)

## Action
Write `backend/services/referral_notification.py` with `send_referral_grant_email()` using Resend.
Modify `referral_reward.py:_grant_sync()` to call it after the Stripe balance transaction.
Write test in `backend/tests/test_referral_notification.py`.

## Expected Impact
Collapses GH #413 checklist from 2 items to 1:
- Item 10 (email notification) → IMPLEMENTED
- Item 9 (user-facing copy) → 30 seconds for human to write
- REFERRAL_REWARD_ENABLED=1 → one Railway env-var flip

Psychological shift: "5 things left on checklist" → "write one sentence, flip one switch."

## Risk
Code change is fully gated by REFERRAL_REWARD_ENABLED env var (not set = impossible to fire in production). Zero risk to activate tenant flow before switch is flipped.

## Autonomy
Requires nightly-commit-review to implement (production Python code change). Human must still set REFERRAL_REWARD_ENABLED=1 after review.
