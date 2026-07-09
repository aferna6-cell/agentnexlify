# Council Ops Checklists — #2 and #9

Two council findings that are not a code fix — they need a business/console
action and a real-world dry run. Code is in place; these runbooks drive it to
"verified in production". Companion to `council-fixes-register.md`.

---

## #2 — Missed-call text-back: verify end-to-end + A2P 10DLC

**State of the code (done):** Twilio voice webhook → `handle_missed_call`
(`backend/routers/twilio_webhooks.py:257`) checks `tenants.textback_enabled`, a
`missed_call_textback` automation row, quiet hours
(`textback_quiet_start/end`), the SMS opt-out ledger and the 24h per-recipient
frequency cap (both added in council #1/#5), then sends via `send_sms`, inserts
a `missed_call_texts` row, and logs activity. Default copy = `DEFAULT_TEXTBACK`;
per-tenant override = `tenants.textback_message`.

**Why this is still open:** 0 sends in production. The path has never been
exercised on a real, carrier-registered number. US carriers now block
application-to-person SMS from numbers without **A2P 10DLC** registration, so
even correct code silently fails to deliver until the number is registered.

**Runbook (do in order):**

1. **Register A2P 10DLC in the Twilio console.**
   - Create/confirm the Twilio Messaging Service.
   - Register the Brand (business EIN/details) and a Campaign (use case:
     "customer care" / missed-call follow-up). Sole-prop low-volume standard
     campaign is the usual tier for these businesses.
   - Attach the sending phone number(s) to the Messaging Service.
   - Wait for campaign = **approved** (hours to days).
2. **Confirm the backend sends through the Messaging Service**, not a bare
   `from` number, so carriers see the registered campaign. Verify `send_sms`
   (`backend/services/twilio_service.py`) / Twilio creds resolve to the
   registered MessagingServiceSid for the test tenant. If it sends from a raw
   number, switch it to the Messaging Service.
3. **Configure the voice number's "a call comes in" / missed-call webhook** to
   point at the deployed `handle_missed_call` route. Confirm the no-answer /
   voicemail path actually hits the webhook.
4. **Enable text-back on a real test tenant**: `textback_enabled = true`, an
   active `missed_call_textback` automation row, sane quiet hours, and a custom
   `textback_message`.
5. **Place a real missed call** from a personal cell during business hours.
   Expect: one text arrives within seconds. Verify a `missed_call_texts` row was
   inserted and an activity entry logged.
6. **Test the guardrails on the live number:** reply **STOP** → confirm the
   number lands in `sms_opt_outs` and a second missed call sends nothing. Call
   twice within an hour → confirm only ONE text (frequency cap). Call during
   quiet hours → confirm no send.
7. **Record the result** in `council-fixes-register.md` #2 with the date, the
   tenant used, and the Twilio campaign SID.

**Done when:** a real missed call produces a delivered text on a 10DLC-approved
number, and STOP / frequency-cap / quiet-hours all behave on the live line.

---

## #9 — Concierge onboarding → self-serve guided wizard (parallel)

**State of the code (done):** the self-serve wizard already exists —
`frontend/src/pages/OnboardingWizardPage.jsx` (express chooser + 6 steps:
business info → auto-KB → services → KB → customize → embed) plus the dashboard
`OnboardingChecklist.jsx`. Website crawl auto-builds the KB; vertical presets and
(new, council #3) an owner-typed description cover no-website businesses.

**Why this is still open:** it is a go-to-market process decision, not a missing
feature. Early customers should get white-glove concierge setup (it converts and
teaches us where the wizard is rough); the wizard runs in parallel so we are
never the bottleneck.

**Runbook:**

1. **Concierge for the first cohort (now):** for each new paid signup, do the
   setup *with* them on a 20-minute call using the wizard — crawl their site (or
   take their description), confirm the KB, drop the embed, place a test missed
   call. Use the real product; do not build a separate manual path.
2. **Log every friction point** the owner hits during concierge into a running
   list (a `docs/dev-knowledge/onboarding-friction.md` or GH issues). Each one is
   a wizard improvement that removes a future concierge minute.
3. **Promote fixes into the wizard** so the self-serve path gets everything we
   learned doing it by hand. Track wizard completion rate via the existing
   onboarding-status endpoint.
4. **Flip the default to self-serve** once the wizard completion rate for a
   cohort clears a bar (e.g. >70% reach "embed installed" without help). Keep
   concierge as an upsell / high-value-account option.

**Done when:** new owners can reach an installed, KB-seeded widget through the
wizard alone, and concierge is a choice rather than a requirement.

---

Updated as these are exercised. See `council-fixes-register.md` for status.
