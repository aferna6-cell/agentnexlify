# Referral Incentive Program — Spec

Status: DRAFT — blocked on owner decisions (§6). Build-ready once §6 is answered.
Author: autonomous loop, 2026-06-23
Related: `brain/Maps/Open Loops.md` (referral channel rounds 12-15), `backend/routers/referral.py`, `backend/services/referral.py`

---

## 1. Goal

Turn the referral channel from *measured* into *incentivized*. Tracking, attribution, signup notification, an admin dashboard, and weekly-digest visibility all shipped (rounds 12-15). The channel works end-to-end but gives the referrer no material reason to share. Add a reward so referring tenants have a concrete payoff, raising referral volume.

Success metric: referred-signup rate (referred signups ÷ active tenants per month) rises after launch. Secondary: share-link click rate per tenant rises.

## 2. Non-goals

- Public/affiliate program for non-tenants (this is tenant→tenant only).
- Cash payouts (Stripe credits/discounts only — no money out the door).
- Multi-level / chain referrals (A refers B refers C → A gets nothing from C).
- Changing the existing attribution mechanics (embed key → `referred_by_widget_key`). Those stay as-is.

## 3. What already exists (reuse, do not rebuild)

| Piece | Location | Reuse for |
|---|---|---|
| Click tracking | `referral_clicks.ref_tenant_id` (migration 157) | attribution input |
| Signup attribution | `tenants.referred_by_widget_key` (migration 159), set at `auth.py` register | who referred whom |
| Referrer resolution | `referred_by_widget_key`→`widget_configs.api_key`→`owner_email` (`services/referral.py`) | who to reward |
| Signup notification email | `notify_referrer_of_signup` (`services/referral.py`) | reward-earned email hook |
| Stripe discount-at-checkout | `billing.py:189`, `auth_billing.py:125` — `session_params["discounts"] = [{"promotion_code": ...}]` | applying a referee-side discount |
| Fraud guard | `services/fraud_guard.py` | self-referral / abuse checks |

## 4. Proposed design (pending §6 confirmation)

Reward on **referee's first successful payment**, not on signup. A signup that never pays is worth nothing and is trivially gamed; gating on first paid invoice (the `checkout.session.completed` / `invoice.paid` webhook already handled in `billing.py:webhook`) makes the reward self-funding and fraud-resistant.

Flow:
1. Referee signs up via share link → `referred_by_widget_key` set (exists today).
2. Referee completes first paid checkout → Stripe webhook fires (handled today in `billing.py`).
3. New hook: on that webhook, if the tenant has a `referred_by_widget_key` AND this is their first paid invoice AND not a self-referral → record a referral reward row + grant the referrer credit.
4. Referrer credit = Stripe **customer balance credit** (negative balance applied to their next invoice) via `stripe.Customer.create_balance_transaction`. Email the referrer "you earned $X credit" (reuse the notify mailer).
5. Optional referee-side perk (double-sided) handled at referee checkout via the existing `discounts` path.

New data: `referral_rewards` table (migration NNN) — `id, referrer_tenant_id, referee_tenant_id, reward_type, reward_amount_cents, stripe_balance_txn_id, status, created_at`, unique on `referee_tenant_id` (one reward per referee, ever). Prevents double-granting on webhook retries (idempotency — pair with existing `services/idempotency.py`).

## 5. Acceptance criteria

- A referred tenant's first paid invoice grants the referrer exactly one reward (idempotent across webhook retries).
- Self-referral (same owner_email or same card fingerprint as referrer) grants nothing — logged, not errored.
- Internal tenants (per `services/internal_tenants.py`) never earn or trigger rewards.
- Reward never applied on signup alone (must be first *paid* invoice).
- Referrer gets an email when a reward is granted.
- Admin referral dashboard (`AdminReferralPage`) shows rewards granted + total credit issued.
- All money math in integer cents. No floats.

## 6. OPEN DECISIONS — owner only (blocks build)

These are business calls, not engineering ones. Build starts once answered:

1. **Reward amount** — flat $X credit per converted referral? (e.g. $20) Or one free month of the referee's plan value? Or % of referee's first payment?
2. **One-sided or double-sided** — referrer only, or also give the referee a first-month discount (stronger conversion, higher CAC)? If double-sided, what referee discount?
3. **Trigger point** — confirm "first *paid* invoice" (recommended, fraud-resistant) vs "on signup" (faster gratification, gameable).
4. **Cap** — max rewards per referrer per month? (fraud ceiling — recommend a cap, e.g. 10/mo.)
5. **Reward mechanic** — Stripe customer balance credit (recommended — auto-applies to next invoice, no code at their checkout) vs a coupon/promotion code they must apply.
6. **Retroactive** — do already-referred signups (the ones tracked in rounds 12-15) earn rewards on their *next* payment, or is this forward-only from launch?

## 7. Rollout

- One migration (`referral_rewards` table).
- Backend-only for the grant path (webhook hook + reward service) — Railway-deployable, no Vercel dependency.
- Admin dashboard addition is the only frontend change (small) — ships when Vercel quota allows.
- Feature-flag the grant behind an env toggle so it can launch dark and be enabled per the owner's go.

## 8. Sequence (once §6 answered)

`GRILL-ME (confirm §6 answers) → migration → referral_rewards service + webhook hook + tests → admin dashboard row → enable flag`
