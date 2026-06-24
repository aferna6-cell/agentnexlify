# Idea 3: In-Widget Referral Prompt Post-Conversion

## Summary
Referral pipeline is fully built through #371 (attribution, admin analytics, notifications, weekly digest). Activate by surfacing the referral link in the widget after lead capture or appointment booking.

## Evidence
- b15071c (#368): referral signup attribution complete — channel measurable end-to-end
- 489eb0f (#369): admin referral overview — per-tenant clicks + referred-signups, ranked
- 1cc3338 (#370): referral signup notification email wired
- 6b1e41c (#371): weekly digest surfaces referral stats
- No in-widget referral prompt exists yet — pipeline built, activation layer missing
- Conversion moment (after form submit) is the highest-intent moment for referral ask

## What "done" looks like
In `widget/agentnexlify-widget.js`, after the success state (lead captured / appointment booked):
- Show optional referral block: "Know a business owner who'd love this? [Share your link]"
- Button copies tenant's referral URL to clipboard (fetched from `/api/referrals/my-link`)
- Dismissable; shown max once per session
- Byte-identical copy to `frontend/public/widget/`

Backend: `/api/referrals/my-link` endpoint returns tenant's referral URL (link generation already exists per #368).

## Impact
Converts the highest-intent moment (post-conversion) into a growth action. Referral pipeline already built — this is activation, not infrastructure.

## Effort
LOW-MEDIUM — ~40 lines widget JS + 1 new API endpoint. Widget byte-identical check required.

## Category
Growth / customer experience
