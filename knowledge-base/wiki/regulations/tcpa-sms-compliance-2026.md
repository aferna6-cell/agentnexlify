---
title: "TCPA SMS Compliance 2026 — One-to-One Consent and the $500-$1,500 Per-Message Penalty"
category: regulations
tags: [tcpa, sms-compliance, fcc, consent, opt-out, 10dlc, statutory-damages]
sources:
  - https://www.signalmash.com/post/tcpa-compliance-sms-2026
created: 2026-04-28
updated: 2026-04-28
summary: "TCPA penalties run $500-$1,500 per non-consented message; FCC's December 2024 one-to-one consent rule killed shared opt-in lists; 8AM-9PM recipient-local-time window and 5-year retention are non-negotiable."
---

The Telephone Consumer Protection Act applies to text messages, and the price of getting it wrong is high enough to end a small business. The statutory range is $500 per unsolicited message, escalating to $1,500 per willful violation. A single campaign blast to 10,000 numbers without proper consent records is a $5M-$15M class-action exposure. Signalmash's 2026 guide makes the practical point clearly: most TCPA violations are not malicious — they come from CRM imports that pulled in numbers without consent metadata, marketing teams who confused transactional consent for marketing consent, or well-meaning sequences that fired before 8AM in the recipient's time zone.

The FCC's December 2024 one-to-one consent rule is the structural change that matters in 2026. Blanket opt-ins covering "marketing partners" or "affiliated companies" no longer satisfy the statute. Consent must be specific to the sender. If a customer opts in on Brand A's website, that consent does not transfer to Brand B even if Brand A and Brand B share a parent company, a CRM, or a contact list. This single rule retired a large category of legacy lead-buying and partner-sharing playbooks overnight, and it forces every consent record to identify the exact business that earned it.

The two-tier consent model is the second concept any operator must internalise. Prior Express Consent covers transactional messages — appointment reminders, order confirmations, shipping updates, account alerts. The bar is implied consent: the customer gave you their phone number in the context of a business transaction, which authorises messages directly related to that transaction. Prior Express Written Consent is the higher bar, required for any promotional message. The written consent must be in writing (electronic signature, web form, keyword opt-in count), must clearly disclose automated text messages, must identify the business by name, must state the message types, must include "message and data rates may apply", and must be voluntary and not a condition of purchase. That last clause is where most checkout flows trip — bundling marketing opt-in into the purchase button is not voluntary consent.

The seven most common mistakes Signalmash catalogues are mostly procedural: buying or renting contact lists (no documented consent for your business), using transactional consent for marketing (sending promos to customers who only consented to order updates), vague opt-in language (form does not explicitly mention SMS), missing opt-out mechanism (no STOP instructions in marketing messages), delayed STOP processing (batch instead of real-time), missing consent records (no timestamp/source/language documentation), and ignoring time-of-day rules (messages outside recipient-local 8AM-9PM window). Each one of these compounds: a flawed CRM import combined with batch STOP processing combined with shared opt-in language is how a single audit produces a five-figure violation count.

Build mechanics are concrete. A compliant opt-in disclosure reads: "By providing your phone number, you agree to receive automated text messages from [Business Name] regarding [message types]. Message frequency varies. Message and data rates may apply. Reply STOP to unsubscribe at any time. Consent is not a condition of purchase." That language must sit visibly next to the phone-number field, not hidden in a terms-of-service link. Maintain separate consent flags for transactional vs marketing. Process STOP in real time across all active campaigns, not in the next batch run. Respect the 8AM-9PM window in the recipient's local time zone — sending at 9PM Eastern to a California number is a violation. Keep records for at least 5 years; the TCPA statute of limitations is 4 years, so the documentation has to outlast it.

State-level overlay adds friction. Florida's Telephone Solicitation Act, California, and Washington each have stricter rules than federal TCPA on timing windows and disclosure language. Carrier-level enforcement runs alongside the statute through 10DLC and toll-free verification programs — TCPA-compliant messages can still be carrier-blocked if 10DLC campaign registration is wrong, and a carrier-clean campaign can still be a TCPA violation. The two regimes overlap but do not substitute. Revocation must be honored within 10 business days under the December 2024 rule, but real-time STOP handling is the only safe operating posture; anything slower is a measurable risk. This sits adjacent to the broader [[us-chatbot-legislation-2026]] regulatory wave hitting AI-mediated communications.

A messaging-provider partnership is a meaningful component of compliance posture in this regime. The CPaaS layer handles STOP keyword automation, opt-out persistence across campaigns, sending-window enforcement, and audit trail generation. Providers that ship compliance support as a first-class concern (Signalmash, Twilio with TCPA add-ons, others) substitute domain expertise that small operators do not have in-house. The cheapest provider on a per-message basis is rarely the right pick when the downside scenario is six-figure litigation exposure.

## Key Concepts

- **One-to-one consent** — FCC December 2024 rule requiring opt-in to be specific to the sender; retired blanket "marketing partners" lists.
- **Prior Express Consent vs Prior Express Written Consent** — transactional bar (implied via business relationship) vs marketing bar (written, specific, voluntary).
- **8AM-9PM recipient-local window** — TCPA timing restriction measured in recipient's time zone, not sender's; stricter in some states.
- **Real-time STOP processing** — opt-out must suppress across all campaigns immediately; batch processing is a documented compliance failure mode.
- **5-year record retention** — required because TCPA statute of limitations is 4 years; consent records must outlast it with timestamp + source + language captured.
- **10DLC vs TCPA** — carrier-level campaign registration regime overlapping with but not equivalent to federal statute; both apply.
- **Statutory damages range** — $500/message baseline, $1,500/message willful; per-message multiplication is what makes class actions catastrophic.

## Related Articles

- [[us-chatbot-legislation-2026]] — broader US legislative wave covering AI-mediated communications including SMS.
- [[gunder-2026-ai-laws-update]] — 2026 AI law update from Gunderson Dettmer; pairs with TCPA on AI-generated messaging compliance.

## Relevance to AgentNexLiFy

The widget collects phone numbers and the chat agent triggers Twilio SMS for missed-call-text-back, appointment confirmation, and auto-follow-up. Every one of those flows touches TCPA. The compliance surface is bigger than most engineering teams price in.

Concrete moves:
1. Audit the consent capture path on the widget. Today the lead-capture form takes phone number; the disclosure language and consent-flag persistence need to match the Signalmash template above and store source + timestamp + exact disclosure text shown.
2. Separate the consent flags in the database. The leads table needs distinct columns for `sms_consent_transactional` and `sms_consent_marketing` (boolean) plus `sms_consent_timestamp`, `sms_consent_source`, `sms_consent_disclosure_text`. Today these may be conflated, which is the most common TCPA failure mode per the Signalmash list.
3. Real-time STOP handling on Twilio inbound webhook. STOP/UNSTOP/HELP keywords need automatic suppression that crosses tenant boundaries — a STOP from a number suppresses all future sends from any AgentNexLiFy tenant for that number, not just the originating one. Anything else is a 10-business-day-revocation race condition.
4. Sending-window guard in `backend/services/automation/scheduled_jobs.py`. Every queued SMS must check recipient phone-number area code → time zone → 8AM-9PM window before send. Missed-call-text-back is the highest-risk path because automation fires reactively without a window check today.
5. Consent record retention for 5 years minimum. Database backups + audit trail must survive that long; coordinate with the schema-log discipline in `docs/dev-knowledge/schema-log.md`.
6. Plan-level positioning: the $250/mo Pro and $899/mo Enterprise tiers should bundle TCPA compliance posture (audit trail export, consent record review tooling) as a feature. Small-business buyers do not understand the regime well; making it visible is a moat against generic competitors who treat compliance as a footnote.
7. Per-tenant onboarding: new tenants must walk through a consent-collection setup before SMS automation activates. The default-on path today is a litigation surface area on day one.
