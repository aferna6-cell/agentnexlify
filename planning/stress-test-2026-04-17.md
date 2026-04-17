# Stress Test — AgentNexLiFy Launch Plan
**Date:** 2026-04-17
**Pattern:** #7 Cynical-operator walkthrough
**Voice:** seasoned SMB-automation founder, watched 50 of these plays since 2019
**Assumes:** rubric score 114/262, 5 testers, widget-first claim, $249/$499/$899 pricing, solo engineer + non-engineer partners, GHL as #1 competitor

---

> "OK. You want to launch a widget-first AI automation platform at SMB pricing, competing against a $97/mo gorilla, solo engineering, no refund flow, no dunning, no IR playbook, no load test, and no kill switch on Claude spend. Let me walk you through exactly how this dies."

---

## Failure Sequence 1 — **First paid customer fires before month 2**

### Week 1 (D+0 to D+7)
Salon owner signs up Growth $249/mo via Stripe checkout. Onboarding wizard (7.3 = 1) works on happy path. Widget embeds on Wix site. First day: 3 leads captured — celebration.

### Week 2 (D+7 to D+14)
Widget answers a booking question incorrectly — tells customer salon is open Sunday when it's not. Customer shows up, shop closed. Owner gets angry Facebook review.

Owner emails support asking "how do I see everything the AI said this week?" Support email (7.2 = `[partner-verify]`) takes 3 days to reply because it's on a partner's personal inbox. First trust hit.

### Week 3 (D+14 to D+21)
Owner wants to cancel. Finds cancel flow in BillingPage.jsx (7.4 = 1 — self-serve exists). No churn survey (10.3 = 0). Clicks cancel. Gets billed **again** next cycle because Stripe `cancel_at_period_end=false` or similar edge you never tested (3.4 = 1).

Owner disputes via chargeback. Stripe chargeback fee = $15. You have no refund flow (3.6 = 0) to pre-empt. Owner's chargeback goes through because you can't prove service delivered with your current logs (4.5 = 0 log retention). Dispute rate for month = 100% (1 of 1).

### Week 5
Stripe flags the account for high dispute rate. Next chargeback = suspend. You have **one customer**, you're now on Stripe's watch list.

### Specific breakpoint
**Not "dunning flow missing"** — breakpoint is: "chargeback cleanup you can't defend because there's no audit log + no refund lever." Stripe dispute rate threshold is 0.75%. At 5 testers → 1 angry customer = company-ending Stripe reputation.

### First fix
Build `POST /admin/refund` + audit log retention ≥30d BEFORE taking second paid customer. 6 hours of work.

---

## Failure Sequence 2 — **GHL undercuts on verticalization, you bleed the mid-market**

### The actual GHL moat
GHL's $97/mo "SaaS Starter" plan lets agencies white-label the platform. Every agency you pitch already has 3 clients on GHL. Your price ceiling is **~$100 or go super-vertical.**

### Month 2
You pitch a contractor (MTOptions-type). They say "we're on GHL for $297. What do you do that GHL doesn't?" Your current pitch: "widget-first, vertical knowledge base, AI answers questions."

GHL comeback: "We have AI Employee for $297 too. Includes email campaigns, SMS, funnels, CRM, courses, membership sites, websites, a mobile app for clients, and a white-label agency platform."

Partner tries to justify $499 Professional. Fails. Prospect chooses GHL or drops to your $249 Growth. You just lost the tier that pays the bills.

### Drillbit move
Drillbit (YC) launches in Q3 with contractor-specific quoting + scheduling + AI receptionist **bundled** for $199. Your one remaining tester (MTOptions — contractor) hears a cold call from Drillbit. Gone.

### Specific breakpoint
**Not "GHL is big"** — breakpoint is the **sales conversation on call 2 minute 7** when the prospect says "what specifically do you do better." Your answer is "widget-first with tenant KB." Prospect hears that as "you have a chatbot." Dead.

### First fix
Pick ONE vertical (salon / dental / contractor / auto shop — given testers are mixed). Drop generic features. Ship a vertical-specific onboarding that takes **90 seconds** to set up vs GHL's 2-hour slog. That is the only differentiation an operator will pay for at $499/mo.

The landing page refresh ("AI that helps run your business") is **more generic**, not more specific. That's a positioning regression if the goal is to fight GHL.

---

## Failure Sequence 3 — **Claude bill eats margin before you notice**

### Current state
No per-tenant usage cap (5.5 = 0). MTOptions already runs 704 msgs/mo at $1.41/mo structured-parser cost. Widget chat on Sonnet (default). No kill switch.

### Month 3
One tester or early customer gets their own site linked from a Reddit thread. 30,000 visitors hit widget in 48h. Each conversation averages 4 turns × ~500 input + ~200 output tokens on Sonnet = ~$0.012/conversation. 30k conversations × $0.012 = **$360 in 48h** for a tenant paying $249/mo.

You find out via Anthropic dashboard 3 days later. Monthly Claude bill: $2,100 across ~8 tenants. MRR: $1,500. **Gross margin: -40%.**

### Second-order
You panic-disable the widget for that tenant. They churn. Public Reddit thread: "AgentNexLiFy turned my widget off when I got traffic." That becomes the first Google result for your brand.

### Specific breakpoint
**Not "Claude is expensive"** — breakpoint is the **48-hour window between cost spike and you noticing**. Your alerting (4.1 = 1) needs RAILWAY_TOKEN. Your uptime monitor (4.3 = 0) doesn't exist. By the time you notice, one tenant has burned 3× their LTV.

### First fix
Per-tenant monthly token cap enforced in `widget_chat.py` before Claude call. Hard stop at 5× plan's baseline. Alert at 3×. 2 hours of work. Higher-leverage than any marketing spend.

---

## Failure Sequence 4 — **Solo engineer hits ER on Friday night**

### Current state
Bus-factor = 1 (10.4 = 0). Partners are non-engineer. No runbook. No dead-man switch (10.5 = 0). Railway + Vercel deploy gated on your credentials.

### Month 4
You're biking home. Get clipped by a car. Broken wrist, surgery Monday. Out for 2 weeks.

Friday night: Stripe webhook secret rotated by Stripe (happens). Payments stop recording. Customers get confirmation emails but no service activation. Partners don't know to rotate `STRIPE_WEBHOOK_SECRET` in Railway because there's no IR playbook (2.8 = 0).

By Monday morning, you have 3 paying customers with silent failures. Partners emailing customers "the engineer is out, we're looking into it." Customers cancel by email.

### Specific breakpoint
**Not "bus factor low"** — breakpoint is the **specific moment a partner opens the Railway dashboard and doesn't know which env var to rotate**. One-page playbook prevents this. Your partners are smart, they just don't know the variable names.

### First fix
`docs/ops/partner-runbook.md` — 1 page, 5 scenarios (Stripe secret rotation, Resend DNS fail, Railway deploy broken, Supabase connection limit, widget disabled emergency). Annotated screenshot per scenario. 2 hours.

---

## What dies first, in order

Most likely sequence of company death (given current state):

1. **Month 1–2: Chargeback explosion** — 1 angry customer + no refund flow → Stripe reputation damage → 80% of future conversion blocked
2. **Month 2–3: Competitor steals mid-market** — GHL/Drillbit answer on the 2nd sales call kills the $499 tier
3. **Month 3–4: Cost spike** — no per-tenant kill switch + first viral tenant = gross margin goes negative
4. **Month 4–6: Bus-factor event** — something mundane (dentist appointment, family emergency, bike crash) + no runbook = partners can't keep service running

Your current rubric says NO-GO. The cynical operator says the rubric **undersells** the problem because it scores each dimension independently. The real killer is how they **chain**.

---

## What the operator would do (specific, not generic)

In priority order, ship BEFORE taking the second paid customer:

1. **Per-tenant cost kill switch** (2h). Cap Claude tokens at 5× plan baseline, alert at 3×. Saves company if tenant goes viral.
2. **Refund endpoint + audit log retention ≥30d** (4h). Pre-empts chargeback cascade.
3. **Partner runbook** — 1 page, 5 scenarios, screenshots (2h). Handles bus-factor event.
4. **Pick ONE vertical** (decision, not code). Re-focus landing + onboarding + pitch on contractors OR salons. Generic "AI that helps run your business" loses to GHL. Ships as copy change (1h) + onboarding variant (4h).
5. **Cancel-reason capture** (1h). One dropdown on cancel modal. Generates the only data that tells you WHY customers leave.

**Total: 14 hours.** Moves rubric from 114 → ~155. More importantly, closes the 4 specific failure sequences above.

---

## What the operator would NOT do

- **No more marketing polish.** OG preview and hero refresh do not save the business. They're already good enough.
- **No more skill scaffolding.** `/go` is fine. Don't build more.
- **No rubric rescore** until the 14 hours above ship.
- **No new feature** until kill switch + refund + runbook exist. Building features without these 3 is building a gun pointed at your own foot.

---

## Three questions for your next partner call

1. Which vertical do we pick by Friday? (pick ONE: contractor, salon, dental, auto shop. All roads lead to ONE.)
2. Who on the partner team has credentials to rotate the Stripe webhook secret without asking me?
3. At what Stripe dispute rate do we pause taking new paid customers? (Set the number now, before month 1.)

---

## The one question I'd ask YOU if I were investing

**"You have 5 testers after 2 months. The top one drives 704 msgs. What specifically happens on the 5th message that makes them PAY you $249 instead of using a $19 Chatbase subscription? Show me that message."**

If you can't screenshot the answer, you don't have product-market fit yet. You have a working prototype. Those are different things. The rubric is a scoreboard for readiness; PMF is the question **behind** the readiness question.

---

*Save this doc. Re-read in 60 days. If the 4 failure sequences haven't been closed, reread #5 again out loud.*
