# Keys Koffee — Voice Sellability Packet (2026-07-13)

Everything needed to sell + switch on the AI phone assistant for Keys Koffee,
with the live prod state verified today.

## Verified prod state (2026-07-13)

| Check | State | Meaning |
|---|---|---|
| Plan | `enterprise` / `active` | Passes the voice plan gate (legacy plan, honored) |
| Widget | active, `booking_enabled=true` | Web channel already live |
| Leads | 3 captured | Demand exists; widget is doing its job |
| Appointments | **0** | Bookings can't convert (see blocker) |
| business_hours rows | **0** | THE blocker — slot generation needs hours (#414/#415) |
| Café KB pack | live in `kb_articles`, FTS-verified | Voice + widget answers are grounded ("do you have oat milk" retrieves it) |
| `twilio_number` | NULL | AI phone line not provisioned yet (owner action, costs a Twilio number) |

## What "voice" means for them now (all shipped + CI-green + deployed)

1. **Answers every call** — grounded on the café KB pack + their FAQ, not generic LLM filler.
2. **Books while talking** — the assistant offers real open slots and books them
   (validated against live availability; hallucinated times can never book).
3. **Dedicated number** — their AI line is its own Twilio number; the owner's
   alert phone stays private (fixed this session — previously these collided).
4. **Metered cost** — live-AI answering caps at `voice_included_minutes`
   (default 300/mo, runtime-tunable, no deploy); over-cap degrades to voicemail,
   never a dropped call. CallsPage shows usage against the allowance.
5. **Owner visibility** — Calls dashboard: transcripts, durations, outcomes,
   minute usage.

## Demo script (5 minutes, phone in hand)

1. **Hook** — "Every call you miss during a rush is a lost sale. This answers
   every one, in your cafe's own voice."
2. **Call the AI line** (after provisioning): ask "do you have oat milk?" —
   grounded answer from the cafe pack, not a canned IVR.
3. **Book live**: "can I book a cake-tasting consult Friday afternoon?" —
   assistant offers real slots, caller picks, appointment lands on the
   dashboard while they watch.
4. **Show the Calls page** — the call they just made: transcript, duration,
   minutes used vs allowance.
5. **Show Knowledge page** — "drop your menu PDF here and the phone assistant
   knows it on the next call." (Bulk upload is live; drag the menu in during
   the demo.)
6. **Close** — "You already have 3 leads from the website widget. The phone
   does the same thing for the 60% of cafe customers who still call."

## Switch-on checklist (owner actions, in order)

1. **Set business hours** (#414/#415) — dashboard Settings -> Hours. Unblocks
   BOTH widget booking (0 appointments today because of this) and voice
   booking. 5 minutes. Do this first; it also un-sticks the #412 funnel.
2. **Provision the AI number** — dashboard Phone page -> Provision. Buys a
   Twilio number into `tenants.twilio_number` (the provision-409 and
   owner-alert defects are fixed as of PR #417).
3. **Decide the pricing story** — `voice_included_minutes` runtime setting
   (default 300/mo). Options: bundle 300 min into their enterprise contract,
   or price voice as an add-on. Setting moves without a deploy.
4. **Optional: forward the shop's public number** to the AI line during
   off-hours only, so voice starts as an after-hours receptionist (lowest-risk
   rollout).

## Risks / honesty notes

- Voice booking is TestClient/CI-verified; no real call has exercised it in
  prod yet. First provisioned number should get a founder test call before
  the customer demo (script step 2 doubles as this).
- Demo-tenant widget chat 500s (#422) — unrelated to Keys Koffee (real-tenant
  path verified live today), but fix before sending prospects to the public
  demo.
