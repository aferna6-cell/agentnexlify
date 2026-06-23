# Cold-Outreach Templates - Top-PMF Verticals (rubric 9.5)

Three single-email cold templates for the highest product-market-fit verticals
per `docs/dev-knowledge/customer-gaps.md`: Salon/Spa (9/10), Plumber/HVAC (8/10),
Dental (8/10).

These are short single-touch templates. For the full multi-touch day 1/3/6/10
sequences, see `outreach/cold-sequences.md`. Same voice, same footer rules, same
CAN-SPAM requirements apply here (real mailing address + working opt-out in every
send - set once at the Instantly campaign level).

Pricing is current: chatbot $19.99/mo, agent_os $99.99/mo. Lead with $19.99 in cold
outreach (the low-friction entry); mention agent_os only when the prospect asks for more.

Placeholders: `{{business_name}}`, `{{owner_name}}`, `{{vertical_pain}}`, `{{city}}`,
`{{demo_url}}`, `{{unsubscribe}}`.

Footer (append at campaign level, do not hand-paste per send):
```
--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

---

## Template 1 - Salon / Spa

Subject: Quick question
```
{{owner_name}} - quick one about {{business_name}}.

When someone wants to book a cut or a facial at 9 PM, or while your team has
their hands full with a client, what happens? Most go to voicemail and book
the next salon in {{city}} instead.

We put an AI front desk on your site that answers instantly, captures the
lead, and books the appointment - 24/7, even when every chair is full.

Built a demo on {{business_name}} so you can see it: {{demo_url}}

$19.99/mo, live in minutes, cancel anytime. Worth a look?
```
(word count: ~95)

---

## Template 2 - Plumber / HVAC

Subject: Quick question
```
{{owner_name}} - when a customer's {{vertical_pain}} at 9 PM and calls
{{business_name}}, what happens?

If it goes to voicemail, they're calling the next company in {{city}} before
they leave you a message. One missed emergency call is a few hundred to a few
thousand dollars walking to a competitor.

We give you an AI front desk that answers every call and chat instantly, gets
the address and the problem, books the slot, and texts you the job - around
the clock.

Built a demo on {{business_name}}: {{demo_url}}

$19.99/mo, no setup, cancel anytime. Take a look?
```
(word count: ~100)

---

## Template 3 - Dental

Subject: Quick question
```
{{owner_name}} - quick question about {{business_name}}.

When a patient lands on your site after hours wanting to book, or calls while
your front desk is mid-checkout, do they become an appointment - or do they
hang up and call another office in {{city}}?

We add an AI front desk that answers instantly, handles the intake questions,
captures the patient, and books the visit - 24/7. It runs on your site and
your phone.

Built a demo on {{business_name}} so you can see it: {{demo_url}}

$19.99/mo, live in minutes, cancel anytime. Worth 60 seconds?
```
(word count: ~95)

---

## Notes for the sender

- `{{vertical_pain}}` for Plumber/HVAC: drop in the specific failure, e.g.
  "AC dies", "pipe bursts", "heat goes out".
- The per-business `{{demo_url}}` is the differentiator. "I built this on YOUR
  business" gets opened; a generic blast gets deleted.
- One vertical per campaign. Test ~100 contacts each, then double down on the
  vertical that replies.
- Keep subject lines casual and lowercase so they read like a real person.
- Owner content gate: confirm the real CT mailing address is set on the Instantly
  campaign footer before the first send. These templates need owner review before
  they go live.
