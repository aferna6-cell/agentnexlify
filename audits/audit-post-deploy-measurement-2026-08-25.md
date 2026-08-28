# Audit — Post-Deploy Measurement Pass (2026-08-25)

Follow-up to `audit-post-deploy-measurement-2026-07-09.md`, 47 days later, against live
prod (project `pxserpybmajixqrmzaly`, queried 2026-08-25 via Supabase MCP). All counts
exclude internal/demo tenants per `internal_tenants.py` (name denylist + `is_demo`).

## Headline numbers (2026-07-09 → 2026-08-25)

| Metric | This window | 07-09 read | Baseline (pre-fix) | Read |
|---|---|---|---|---|
| Chat messages (real tenants) | 224 | 283 (16d) | 2,717 lifetime | ~4.8/day, down from ~18/day |
| Leads captured | 19 | 7 | 27 lifetime | — |
| Msg→lead conversion | **8.5%** (19/224) | 2.5% | ~1.0% | **Lead-capture fix compounding: 8.5x baseline** |
| Real appointments | **3** (lifetime total 3) | 0 real ever | 0 | **First real bookings in product history** |
| Lead→booking conversion | 15.8% (3/19) | 0% | 0% | Booking-nudge fix now validated on real tenants |
| New tenant signups | 0 | 0 | — | Distribution remains THE binding constraint |
| Real paid tenants | 4 | ~3 | — | Niko's Consulting converted to `chatbot` (was abandoned signup on 07-09) |
| Referral clicks | 1 | 3 | — | Channel alive, negligible volume |

## Finding 1 — both conversion fixes are now validated on real traffic

- **Lead capture:** 1.0% → 2.5% → **8.5%**. MTOptions alone: 204 msgs → 17 leads (8.3%).
  914 Exterior: 18 msgs → 2 leads (11%). No further prompt iteration warranted; the
  prompt is no longer the funnel bottleneck.
- **Booking:** the 07-09 open question ("prompt problem vs config problem vs UX?") is
  answered — none of the three. It was traffic + time. 914 Exterior booked 2 real
  appointments, MTOptions 1. `booking_enabled` is true on all three enterprise tenants.

## Finding 2 — one paid conversion, and two silent paid tenants

- **Niko's Consulting** converted from abandoned free signup to paid `chatbot`
  (plan_status active) — but has **0 chat messages in 47 days** and
  `booking_enabled` false (correct for chatbot plan). Paying + zero usage = the
  highest-priority churn risk on the books.
- **Keys Koffee** (enterprise): 2 messages in 47 days. Near-dormant.
- Both will surface on the upgraded churn-watch call list (this PR): last-activity
  date + ready-to-send re-engagement draft in the Sunday owner email.

## Finding 3 — message volume dropped ~4x; distribution still unsolved

~18 msgs/day (06-23→07-09) fell to ~4.8/day. Zero new signups in 47 more days despite
12 live SEO vertical pages. Conversion is now good enough that traffic is the whole
game: at 8.5% msg→lead, every ~12 visitor messages produce a lead. The cold outreach
engine (owner-gated: `GOOGLE_PLACES_API_KEY` in Railway + Instantly creds) remains the
highest-leverage unshipped asset.

## Changes shipped with this audit

1. `compute_funnel()` now reports `new_messages_week`, `msg_to_lead_rate_week`,
   `lead_to_appt_rate_week`; the Monday weekly funnel email renders both rates —
   this measurement pass becomes continuous instead of a manual prod-query session.
2. Churn-watch Sunday alert upgraded to a call list (last activity, owner email,
   plan MRR at stake, per-tenant re-engagement draft; drafts-only, nothing auto-sent).
3. Annual prepay billing (2 months free) shipped as a conversion/retention lever —
   `chatbot` $199.90/yr, `agent_os` $999.90/yr (see PR).

## Verification

- Prod queried live via Supabase MCP 2026-08-25 (tenants, chat_messages, leads,
  appointments, referral_clicks, widget_configs), internal/demo exclusion applied
  in-query with the same patterns as `internal_tenants.py`.
- `pytest backend/tests/test_funnel_metrics.py test_weekly_funnel_report.py
  test_funnel_conversion_rates.py test_churn_watch.py test_churn_watch_call_list.py
  test_billing_annual.py test_billing_amount_to_plan.py --noconftest` — all green
  (see PR test summary).
