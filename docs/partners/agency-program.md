# AgentNexLiFy Agency / Reseller Program (launch terms, 2026-08-25)

One agency managing local-business clients is worth 10-20 direct sales. This
page holds the launch terms; adjust before signing the first partner if
needed — nothing here is hard-coded except the white-label feature itself
(already an `agent_os` premium gate).

## Offer

| Seats (client accounts) | Partner price per seat | vs retail $99.99 |
|---|---|---|
| 1-4 | $99.99/mo (retail) | — |
| 5-14 | $79.99/mo | 20% off |
| 15+ | $69.99/mo | 30% off |

- **White-label included** on every seat (agency's branding on widget +
  dashboard — the existing agent_os white-label gate).
- Agency bills its own clients at whatever retail it chooses (typical:
  $199-297/mo — the margin is the agency's incentive).
- Partner discount mechanics: Stripe coupon applied to the agency's
  subscriptions (owner creates the two coupons in Stripe when the first
  partner signs — no code needed).
- No certification or minimum term at launch; month-to-month.

## Why an agency says yes

- They resell an AI receptionist their clients ask about, without building it.
- Vertical KB packs (13 industries) mean setup per client is minutes.
- Their alternative is GoHighLevel at $497/mo for the white-label tier.

## Pipeline

- Inquiries arrive from the marketing site /partners page →
  `POST /api/v1/partners/inquiry` → owner email (reply directly).
- Qualify on one call: how many clients, which verticals, who does setup.
- Close: create their seats as normal tenants under their accounts, apply the
  partner coupon, flip white-label on.

## Outreach angle (for the cold engine)

Target: local marketing agencies + web designers serving our 13 verticals.
The pitch is margin: "add a $200/mo line item to every client you already
have, at $79.99 cost, white-labeled as yours."
