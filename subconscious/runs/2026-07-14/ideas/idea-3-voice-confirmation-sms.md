# Idea 3 — Voice G3 Post-Call Booking Confirmation SMS

## Category
customer_value

## Effort
M (requires tracing voice booking flow and wiring to reminder system)

## Evidence
- commit c41b318 (merge PR #417, recent): Voice G3 complete — AI phone books real appointments
- `twilio_number` column added to tenant config
- Existing appointment reminder system handles SMS via Twilio
- AdminFunnelPage Booked stage live (PR #417) — shows 0/3 tenants ever booked
- Industry standard: booking confirmation text within 2 min (dental, salon, HVAC all expect this)

## Action
After voice call produces a confirmed booking:
1. Identify the appointment just created by the voice flow
2. Call existing appointment confirmation trigger (same SMS that fires for widget bookings)
3. Deliver "Your appointment at [tenant] is confirmed for [datetime]. Reply CANCEL to cancel." to caller's phone

## Expected Impact
First voice booking (whenever Keys Koffee or other tenant activates) gets professional confirmation.
Reduces voice booking no-shows (unconfirmed appointments have 3-5x higher no-show rate).
Tenant sees immediate value from Voice G3 investment.

## Risk
Medium. Requires tracing voice booking code path (c41b318). Twilio costs per SMS (already priced into plans). Edge case: caller hangs up before call_sid resolves.

## Autonomy
Requires nightly-commit-review to implement (production Python code). No human approval needed for implementation but higher risk than idea 2 (behavior change in production voice flow).

## Note
Premature until first voice booking occurs. Zero voice bookings in production today (0/3 tenants configured). Lower urgency than ideas 1 and 2.
