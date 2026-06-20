# AgentNexLiFy Cold Email Sequences

Three vertical sequences for cold outbound. Built for deliverability and reply rate:
plain text, one idea per email, one soft CTA, pain-first. No images, no HTML, no
"Transform your business with AI."

## How to use
- Send from a separate outbound domain (e.g. `getagentnexlify.com`), never the primary.
- Warm the domain ~2 weeks first. Then 30-50/inbox/day.
- One vertical per campaign. Test ~100 contacts each.
- Merge fields (Instantly/Smartlead style): `{{first_name}}`, `{{company}}`, `{{city}}`, `{{demo_url}}`.
  `{{demo_url}}` comes from the lead-engine CSV (a per-business demo link).
- Spacing: Day 1, Day 3, Day 6, Day 10. Stop the sequence on any reply.
## CAN-SPAM compliance (required before sending)
US cold email is legal only with all three:
1. **A real physical mailing address** in every email (PO box is fine).
2. **A working opt-out** in every email.
3. **Accurate from-name + subject** (already handled by the copy).

The footer below is on every email in this doc. **In Instantly, set it once at the
campaign level** (Settings -> add your address + enable the unsubscribe link) so it
auto-appends — you don't hand-paste it per send. `{{unsubscribe}}` is Instantly's
opt-out merge tag; the "reply STOP" line is a courtesy that also works. Replace the
address placeholder with your real CT mailing address before the first send.

Footer (already appended to every email below):
```
--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

---

## Sequence A - Roofing / Contractors

### Email 1 (Day 1)
Subject: Quick question
```
{{first_name}} - quick one.

What happens when someone needs a roof quote and calls {{company}} at 8 PM,
or while you're up on a job and can't grab the phone?

Right now they probably call the next roofer in {{city}}.

We put an AI front desk on your site and phone that answers instantly, captures
the lead, and books the estimate - 24/7, even when you're on a roof.

I built a quick demo on your business so you can see it: {{demo_url}}

Worth a look?

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

### Email 2 (Day 3)
Subject: re: Quick question
```
{{first_name}} - the math that made me reach out:

One missed call for a roof job is a few thousand dollars walking to a competitor.
Most contractors miss a third of their calls (jobs, weather, after hours).

The AI catches those, texts you the lead, and books the estimate while you work.

Demo on {{company}}: {{demo_url}}

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

### Email 3 (Day 6)
Subject: missed calls = missed roofs
```
{{first_name}} - not trying to sell you software.

Trying to stop {{company}} from losing the 8 PM "my roof is leaking" call to the
next guy. The AI answers, qualifies, and books. You see the lead in the morning.

$19.99/mo, no setup, cancel anytime. Live in under 10 minutes.

Want me to turn it on for {{company}}?

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

### Email 4 (Day 10 - breakup)
Subject: should I close this out?
```
{{first_name}} - haven't heard back, so I'll assume the timing's off.

If missed after-hours calls ever become a problem, the demo's here: {{demo_url}}

I'll leave you alone. Good luck with the busy season.

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

---

## Sequence B - Home Services (HVAC / Plumbing / Electrical)

### Email 1 (Day 1)
Subject: Quick question
```
{{first_name}} - when a customer's AC dies at 9 PM and calls {{company}}, what happens?

If it goes to voicemail, they're calling the next HVAC company in {{city}} before
they leave you a message.

We give you an AI front desk that answers every call and chat instantly, captures
the lead, and books the service call - around the clock.

Built you a demo on {{company}}: {{demo_url}}

Take a look?

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

### Email 2 (Day 3)
Subject: re: Quick question
```
{{first_name}} - emergencies don't wait for business hours, and that's exactly when
people call.

The AI picks up after hours, gets the address and the problem, books the slot, and
texts you the job. No more "I called but nobody answered."

{{company}} demo: {{demo_url}}

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

### Email 3 (Day 6)
Subject: the after-hours leak
```
{{first_name}} - one burst pipe call you miss tonight is a $400-2,000 job gone.

The AI answers it, books it, and hands it to you. Works on your site and your phone.

$19.99/mo, live in minutes, cancel anytime.

Want it on for {{company}}?

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

### Email 4 (Day 10 - breakup)
Subject: should I close this out?
```
{{first_name}} - I'll stop here.

If after-hours calls ever start slipping through, the demo's ready: {{demo_url}}

Appreciate your time.

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

---

## Sequence C - Insurance Agencies

### Email 1 (Day 1)
Subject: Quick question
```
{{first_name}} - quick question about {{company}}.

When a prospect lands on your site at night wanting a quote, or calls while your
team is with another client, do they become a lead - or do they bounce to a
national 800 number?

We add an AI front desk that answers instantly, qualifies the prospect, and books
the call - 24/7.

Built a demo on {{company}} so you can see it: {{demo_url}}

Worth 60 seconds?

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

### Email 2 (Day 3)
Subject: re: Quick question
```
{{first_name}} - insurance is a speed-to-lead game. First agent to respond usually wins.

The AI responds in seconds every time, day or night, captures the contact, and books
the appointment before they shop the next agency.

{{company}} demo: {{demo_url}}

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

### Email 3 (Day 6)
Subject: speed to lead
```
{{first_name}} - the prospects you lose aren't unqualified. They just talked to
someone else first.

The AI makes {{company}} the first responder, every time. Captures and books while
your team focuses on writing policies.

$19.99/mo, no setup, cancel anytime.

Turn it on for {{company}}?

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

### Email 4 (Day 10 - breakup)
Subject: should I close this out?
```
{{first_name}} - I'll assume now's not the time.

If speed-to-lead ever becomes the bottleneck, the demo's here: {{demo_url}}

Thanks for reading.

--
AgentNexLiFy, [your mailing address, City, ST ZIP]
Not relevant? Reply STOP or unsubscribe: {{unsubscribe}}
```

---

## Notes
- Keep subject lines lowercase / casual ("Quick question") - they read like a real person, not a blast.
- The `{{demo_url}}` per-business demo link is the differentiator. A generic email gets deleted; "I built this on YOUR business" gets opened.
- Track reply rate and positive-reply rate per vertical. Double down on whichever of the three responds; kill the others.
- A/B the Email 1 subject ("Quick question" vs a pain-specific one) once you have volume.
