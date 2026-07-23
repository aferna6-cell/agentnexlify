---
title: "TCPA Text Message Rules 2026 — PEWC, Exemptions, and the Litigation Surge"
category: regulations
tags: ["tcpa", "sms", "consent", "pewc", "compliance", "twilio"]
sources: ["raw/regulations/activeprospect-tcpa-text-messages-2026.md"]
created: 2026-07-23
updated: 2026-07-23
summary: "TCPA lawsuits rose ~27% into 2026 on top of a 95% surge in 2025; marketing SMS still requires prior express written consent with auditable records, quiet hours run 8am–9pm recipient-local, penalties run $500–$1,500 per message, and informational texts (appointment reminders) sit under the lower prior-express-consent standard."
---

# TCPA Text Message Rules 2026 — PEWC, Exemptions, and the Litigation Surge

TCPA enforcement is accelerating, not settling: lawsuits rose nearly 27% to start 2026 after litigation "surged by 95% in 2025 alone," at $500–$1,500 statutory damages per message with class-action exposure. The 2026 compliance baseline for marketing SMS remains Prior Express Written Consent (PEWC): a clear disclosure naming the company, stating message categories and data rates, stating that consent is not a purchase condition, and specifying the phone number — simple call-to-action opt-ins ("Text SAVE to 54321") have faced litigation challenges as insufficient. One structural loosening carried into 2026: the 11th Circuit vacated the FCC's one-to-one consent rule (Insurance Marketing Coalition v. FCC, Jan 24, 2025), so per-seller individualized consent is no longer federally required, though the underlying PEWC standard stands. This updates the baseline captured in [[tcpa-sms-compliance-2026]].

The consent-tier distinction is the load-bearing rule for chat-widget products. **Informational** texts — appointment reminders, confirmations, account updates, delivery notifications — need only Prior Express Consent (PEC), which can be collected orally or by a customer providing their number in context. **Marketing** texts — discounts, promotions, product announcements — need written consent with the full disclosure stack. Healthcare messages (appointment confirmations, prescription notices) sit in a HIPAA-adjacent exemption category still requiring PEC; only true emergencies need no consent. Operational rules on top: quiet hours 8am–9pm in the *recipient's* time zone (states can be stricter), opt-outs processed within 10 business days with STOP as the standard mechanism, DNC and Reassigned Number Database scrubbing before sends, and auditable consent records (date, time, method, exact language shown; for third-party leads, IP address + timestamp + a screenshot of the consent language).

The article's template language is directly reusable: marketing consent — "By checking this box, you agree to receive recurring automated promotional and personalized marketing text messages… Consent is not a condition of purchase. Msg & data rates may apply. Msg frequency varies. Reply HELP for help, STOP to cancel." Informational consent — "By providing your number, you consent to receive automated service-related messages (e.g., appointment reminders)…" — with the caveat that template language alone is not compliance and legal review is required. Two regimes govern simultaneously: TCPA (FCC-enforced law) and CTIA carrier guidelines (carrier-enforced, e.g. SHAFT content rules) — passing one does not satisfy the other.

## Key Concepts

- **PEWC (Prior Express Written Consent)** — the written, disclosure-complete consent standard for marketing SMS; the highest consent tier and the one most litigated.
- **PEC (Prior Express Consent)** — the lower standard covering informational/transactional texts; a customer providing their number in a service context generally suffices.
- **One-to-one consent vacatur** — the 11th Circuit's Jan 2025 decision striking the FCC rule that consent must name each individual seller; reduces lead-gen compliance burden but not PEWC itself.
- **Quiet hours** — no messages before 8am or after 9pm recipient-local time; nationwide sends must be time-zone aware.
- **RND (Reassigned Number Database)** — FCC database for checking whether a number changed owners; texting a reassigned number voids the prior owner's consent.

## Related Articles

- [[tcpa-sms-compliance-2026]] — earlier TCPA baseline this article updates with 2026 litigation data and consent templates.
- [[hipaa-ai-chatbot-compliance-2026]] — the parallel healthcare compliance regime for medical/dental tenant messaging.
- [[us-chatbot-legislation-2026]] — state chatbot-disclosure laws that stack on top of TCPA for widget conversations.

## Relevance to AgentNexLiFy

Our Twilio SMS paths (appointment reminders, follow-up automations, marketing sequences) span both consent tiers, and the product must enforce the boundary per message type: reminders and booking confirmations ride PEC collected by the widget ("By providing your number…" microcopy — verify our widget lead form shows it), but any `agent_os` marketing/re-engagement sequence needs PEWC capture with stored proof. Engineering checklist: (1) consent-tier flag on each outbound SMS template; (2) consent audit log (timestamp, method, exact language, IP) on the leads record; (3) quiet-hours guard using recipient timezone before any automation send; (4) STOP handling already required by Twilio — confirm it also halts our automation sequences, not just Twilio-level delivery. The 27% litigation growth means "tenant misconfigured their campaign" is our risk too — compliance guardrails in the product are a sellable feature for the white-label tier.
