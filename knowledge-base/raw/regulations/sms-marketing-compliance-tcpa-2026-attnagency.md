---
title: SMS Marketing Compliance in 2026 — TCPA, Opt-In Rules & Best Practices
date: 2026-03-05
source_url: https://www.attnagency.com/blog/sms-marketing-compliance-2026
fetched_at: 2026-08-26
category: regulations
tags: [tcpa, sms, opt-in, consent, stop-keyword, quiet-hours, 10dlc, audit-trail, twilio, hipaa]
---

# SMS Marketing Compliance in 2026: TCPA, Opt-In Rules & Best Practices

*ATTN Agency. 2026-03-05.*

## Exposure

- Statutory damages **$500 per message**, up to **$1,500 per willful violation**; no cap; class-action friendly.

## Express written consent — required elements

1. Program name and what the consumer is signing up for
2. Message frequency ("up to 4 msgs/mo" or "recurring")
3. "Msg & data rates may apply"
4. STOP to cancel / HELP for help
5. Business contact info
6. Signature or affirmative confirmation (checkbox, keyword reply, e-sign)

## What does NOT count as consent

- Pre-checked boxes
- Consent forced as a condition of purchase
- Vague or buried language
- Oral consent alone
- Purchased or rented lists

## Sample compliant opt-in copy (from article)

> By checking this box you agree to receive recurring automated marketing texts from [Business] at the number provided. Consent is not a condition of purchase. Msg frequency varies. Msg & data rates may apply. Reply STOP to cancel, HELP for help. [Privacy] [Terms]

Variants given for checkout, popup, and keyword ("Text JOIN to 12345") flows. Double opt-in (confirm via reply) recommended.

## Opt-out handling

- Process STOP within **5 minutes** and send one confirmation.
- Honor alternates: QUIT, END, CANCEL, UNSUBSCRIBE, plus reasonable natural-language ("stop texting me").
- Retain opt-outs **permanently**.

## Timing

- Send window **8 am – 9 pm recipient local time** (federal). State variations noted for CA, NY, FL, TX (Florida 8 am–8 pm, and per-day caps in some states).

## Transactional vs promotional

Appointment reminders, confirmations, and service-status texts are transactional — lower consent bar, but still need STOP handling and must not include marketing content.

## Audit trail

Store per consent: timestamp, IP, capture method, exact disclosure language shown, source page/campaign. Retain consent records **7 years**.

## Other

- Healthcare senders add HIPAA (no PHI in texts without safeguards).
- Vendor contracts: indemnification + audit rights.
- Violation response protocol: stop sends, preserve records, counsel, remediate.
- International: GDPR (EU), CASL (Canada), Spam Act (Australia) notes.
- 2026 checklist included.

## Notes for AgentNexLiFy

- Directly governs missed-call text-back, auto-follow-up, and appointment reminders on Twilio.
- Must build: consent record table (timestamp, IP, method, language, source), STOP/keyword handling within 5 min (Twilio Advanced Opt-Out or our own), quiet-hours enforcement per tenant timezone, transactional vs promotional message classification.
- Widget lead-capture consent checkbox copy needs the six elements; unchecked by default.
- Pairs with `raw/regulations/tcpa-sms-compliance-2026-signalmash.md` and `activeprospect-tcpa-text-messages-2026.md`.
