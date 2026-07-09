# Audit — Post-Deploy Measurement Pass (2026-07-09)

The 2026-06-23 session shipped the conversion/GTM backlog (PRs #358–#370) and explicitly
deferred iteration until real post-deploy usage data existed. This is that measurement,
16 days later, against live prod (project `pxserpybmajixqrmzaly`, queried 2026-07-09).

## Headline numbers (2026-06-23 → 2026-07-09)

| Metric | Value | Baseline (pre-fix) | Read |
|---|---|---|---|
| Chat messages | 283 | 2,717 lifetime | ~18/day; Smoke Test is 124 of the 283 (44%) — still polluting |
| Leads captured | 7 | 27 lifetime | — |
| Msg→lead conversion | 2.5% (7/283) | ~1.0% (27/2717) | **Lead-capture prompt fix works: ~2.5x improvement** |
| MTOptions alone | 4 leads / 125 msgs = 3.2% | — | Best real-tenant signal |
| Real appointments | **0** | reported "9" | **All 9 prod appointments are demo-seeded** (see below) |
| New tenant signups | **0** | — | Zero in 16 days — distribution is the binding constraint |
| Referral clicks | 3 (2 on 06-24, 1 on 07-06) | 0 | Channel alive, negligible volume |
| Referred signups | 0 | 0 | No signups at all, so expected |
| error_events rows | 0 | — | No captured errors (or low traffic) since migration 156 |
| wizard_events | 5 rows, all step 1, last 2026-05-27 | — | Instrumentation fine; silence = zero wizard traffic, not a bug |

## Finding 1 — booking conversion was never 33%; it is 0%

All 9 appointments in prod were created 2026-07-09 (demo-refresh job) and belong to the
three `(DEMO)` tenants (Luxe & Co. Salon, Reliable Plumbing Co., Summit Trading Alerts —
3 each). The June "27 leads → 9 appointments = 33% booking conversion" read was
demo-data pollution. **No real customer has ever booked an appointment through the
widget.** The booking-nudge prompt work shipped 06-23 has produced 0 bookings on 7 real
leads since.

Fix shipped with this audit: `is_internal_tenant()` now also excludes `(demo)`-named
tenants and honors the `tenants.is_demo` flag, so funnel/tenant-health/churn metrics
stop counting demo seeds. (`backend/services/internal_tenants.py` + 6 tests.)

Follow-up (next session): trace the booking flow on a real tenant end-to-end —
7 real leads with 0 booking offers accepted is either a prompt problem, a
booking-enabled config problem on real tenants (MTOptions/914 Exterior may have
`booking_enabled` off or no service types), or a UX problem.

## Finding 2 — lead capture improved ~2.5x; the fix is validated

283 msgs → 7 leads (2.5%) vs ~1.0% lifetime baseline; MTOptions at 3.2%. Small n, but
directionally clear. No further prompt iteration warranted until traffic grows.

## Finding 3 — zero signups in 16 days; distribution is provably the constraint

12 tenants, 0 new since 06-23, despite live domain + 12 SEO vertical pages. wizard_events
silence is explained by zero traffic, not broken instrumentation (constraints verified
live: step 0–7, `demo_referral` allowed — both duplicate-158 migrations ARE applied,
GH #373 resolved).

The 5 `free`-plan tenants remain: 3 internal + 2 abandoned signups (Sunset Mobile
Detailing, Niko's Consulting) — the abandoned two remain the only warm recovery targets.

## Finding 4 — paid-tenant count includes demo/internal accounts

`plan != 'free' AND plan_status IN ('active','trialing')` counts 8, but that includes
3 `(DEMO)` professional tenants and 2 internal "Agent Nexlify" accounts. Real paying
external tenants ≈ 3 (MTOptions, 914 Exterior LLC, Keys Koffee). The funnel dashboard
will show the corrected number once the demo exclusion deploys.

## Verification

- Prod queried live via Supabase MCP 2026-07-09 (tenants, chat_messages, leads,
  appointments, referral_clicks, wizard_events, error_events, pg_constraint).
- `pytest backend/tests/test_internal_tenants.py test_funnel_metrics.py
  test_tenant_health.py test_churn_watch.py --noconftest` — 112 passed.
