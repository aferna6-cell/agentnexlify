# Audit: Revenue Funnel — 2026-07-23

**Scope:** widget → conversation → lead → booking, all 3 paying tenants, live prod probes + SQL + code trace.
**Headline finding:** the `appointments` table contained only seeded DEMO rows. **Zero real bookings ever, platform-wide** — not a regression; the funnel never converted once.

## Per-tenant state (30 days, as found)

| | Keys Koffee | MTOptions | 914 Exterior |
|---|---|---|---|
| Conversations / msgs | 0 / 0 (dead since 2026-06-14) | 38 / 194 | 4 / 18 |
| Leads (`client_id`) | 0 | 10 — all stuck `status='new'` | 1 |
| Bookings | 0 | 0 | 0 |
| Widget on live site | **NO — embed missing** | yes | yes |
| Slots API | 200 after same-day hours seed | 200 | 200 |
| `business_slug` | NULL (fixed same day) | `mtoptions` | NULL (fixed same day) |

## Root causes (ranked)

1. **Booking CTA rendered as unclickable plain text.** `booking_prompt.py` told the model to share a bare URL; the widget's `_inlineMd()` only linkifies markdown `[text](url)`. ~0% click-through on the only booking path the AI could offer. **FIXED** (PR #571): prompt emits `[Book an appointment](url)`, regression test pins it.
2. **The AI could not open the native booking panel** — panel opened only on a user-text keyword regex (`/book|appointment|.../`). Visitors who never type a booking keyword never saw it. **FIXED** (PR #574): `SHOW_BOOKING_PANEL` marker → `show_booking` response flag → `showBooking("date")`, mirroring the `HANDOFF_REQUESTED` pattern.
3. **Keys Koffee's widget silently vanished from their site ~June 14** (site redeploy dropped the embed) and no alerting noticed a paying tenant at zero traffic for 5+ weeks. Config side fixed (default hours seeded, slug set, 16 slots live); embed re-install is with the tenant (email drafted). Alert gap tracked in #573's companion item ("paying tenant, 0 conversations in 7 days").
4. **Missing `business_slug`** on 2 of 3 tenants → booking pages 404'd and the prompt degraded to contact-capture. **FIXED** in prod (`keys-koffee`, `914-exterior`; all three `/api/v1/book/*` return 200).
5. **Sales-ops, not code:** MTOptions' 10 contact-complete leads sat untouched at `status='new'`; conversation alerts route to Aidan's inbox (intentional — in-family tenant), lead-alert follow-through is the gap. Owner email drafted with the de-duped 7 contactable leads.
6. **Traffic:** 914 Exterior (4 conv/mo) and Keys Koffee (0) are marketing problems no funnel fix converts.

## Verification trail
- Slots: `GET /api/v1/appointments/slots/{tenant}?date=…` → 16 slots (Keys Koffee) same day as hours seed.
- Booking pages: 200 × 3 post-slug fix.
- Deployed widget on www.agentnexlify.com byte-identical (md5) to repo mirrors.
- Audit probes created 2 conversations (`audit_fable5_20260723_mto`, `_914`) + 4 chat_messages/session; no leads/appointments/SMS side effects; 1 notify email to aidanfernandes31@.

## Follow-ups
- [x] Markdown booking link (PR #571, merged)
- [x] `business_slug` for 2 tenants (prod config)
- [x] Keys Koffee hours + bookability (#415 closed)
- [ ] PR #574 merge (panel trigger) — in review
- [ ] Tenant-silence alert (#573 companion; next `ai-ready` candidate)
- [ ] Keys Koffee embed re-install (tenant action; email in drafts, snippet included)
- [ ] MTOptions lead follow-up (owner action; email in drafts)
