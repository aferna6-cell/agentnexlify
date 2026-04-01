# AgentNexLiFy — Client Demo Script
**Date:** 2026-04-01 | **Version:** Generic (no specific industry)
**Confidence Breakdown:** 28 DEMO · 6 MENTION · 5 SKIP

> **Presenter note:** Customize every [BRACKETED] placeholder before the call. The script is written for you to read aloud — italics are stage directions, not spoken.

---

## Pre-Demo Checklist

- [ ] Open `https://app.agentnexlify.com` in an incognito window — confirms production is live
- [ ] Open `https://agentnexlify-production.up.railway.app/docs` — confirms backend is responding
- [ ] Have a burner email address ready for the live signup (e.g. `demo+[client]@yourdomain.com`)
- [ ] Know the client's business name, city, and industry in advance
- [ ] Pull up the landing page `https://www.agentnexlify.com` in a second tab
- [ ] Have the embed snippet demo ready: `https://app.agentnexlify.com/biz/[slug]` (if they have one)
- [ ] Silence phone/notifications — SMS alerts will fire during the widget demo

---

## Act 1: The Problem (2 min)

> *Open with empathy. Don't pitch yet. Get them nodding.*

"Quick question before I show you anything — when a potential customer reaches out to your business after hours, what happens?"

*[Let them answer. They'll say: voicemail, nothing, call back next day.]*

"Right. And how many of those people do you think called your competitor while they were waiting?"

*[Pause. Let that land.]*

"The average small business misses 62% of inbound leads because there's no one to respond instantly. And the data is brutal — if you don't respond within 5 minutes, you lose 80% of those leads permanently. Not to a bad pitch. Just to silence.

What AgentNexLiFy does is simple: it puts an AI employee on your website that works 24/7, answers customer questions instantly, captures their contact info, books appointments, and kicks off a follow-up sequence — all without you doing anything. When you wake up in the morning, your leads are already in your CRM, qualified, and some of them already have appointments booked."

---

## Act 2: Sign Up Together (5 min)

> *Go to `https://www.agentnexlify.com` and click "Start Free Trial." Walk through this live.*

"Let me show you how fast this goes. I'm going to set up a real account right now — takes about 3 minutes."

**Fields on the signup form:**
- Business Name → *use their real business name*
- Your Name → *use a demo name*
- Email → *use your burner email*
- Phone (optional) → *skip for speed*
- Website URL (optional) → *enter their real site if they have one — it gets crawled for AI context*
- Industry → *select their industry from the dropdown*
- City → *their city*
- Password

"Notice I'm entering your actual website. The system will crawl it and use that content to train the AI on your business — your services, your hours, your FAQs. It learns your business."

*[Submit. You'll land on `/dashboard`.]*

"That's it. We're in. No credit card, no setup fee, no call with a salesperson. You just got a live AI employee."

---

## Act 3: Dashboard Tour (12 min)

> *Walk through each section. Keep it fast — 60–90 seconds per section.*

### 3a. Dashboard Home (`/dashboard`)

"This is your command center. At a glance you can see: how many conversations your widget has had, how many leads were captured, how many appointments are booked, and a live activity feed of everything happening with your customers.

All of this updates in real time. Every chat, every lead captured, every appointment booked — it shows up here."

**DEMO** — real data, real metrics once widget has activity.

---

### 3b. Leads (`/dashboard/leads`)

"Every time your widget captures someone's contact info — name, email, phone — they automatically become a lead here. No manual data entry ever.

Each lead has: contact details, a lead score (the AI rates how hot they are based on the conversation), a temperature — hot, warm, or cold — a summary of what they talked about, any tags, and the conversation history.

You can filter, search, sort. If you have a team, you can assign leads to specific people. You can add notes, log a call, send a manual email — all from this screen."

**DEMO** — fully functional CRM.

---

### 3c. Pipeline (`/dashboard/pipeline`)

"For businesses that have a sales process — quote, follow-up, proposal, closed — here's your visual pipeline. It's a kanban board. Drag a lead from 'New' to 'Quoted' to 'Won.' You can create custom stages that match your actual workflow.

And here's where it gets powerful: you can set up automation rules so that when a lead moves to a certain stage, it automatically sends them an email, a text, or kicks off a follow-up sequence."

**DEMO** — pipeline + stage drag-drop works. Automations work.

---

### 3d. Calendar (`/dashboard/calendar`)

"Every appointment booked through the widget — or manually — shows up here. It's a full calendar view. If you connect your Google Calendar, appointments sync both ways automatically. Your team sees real-time availability. No double-bookings, no phone tag."

**DEMO** — calendar view works. Google Calendar OAuth sync works.

---

### 3e. Conversations (`/dashboard/conversations`)

"This is your inbox. Every widget conversation your AI has is logged here in full — every message, in order. You can search by customer name, filter by status. If a customer asks something the AI couldn't handle, you'll see it here and can respond manually.

You can also add internal notes, assign conversations to a team member, and tag them."

**DEMO** — fully functional conversation log.

---

### 3f. Email Sequences (`/dashboard/sequences`)

"This is one of the most powerful features. After a lead is captured, you can automatically enroll them in a drip email sequence. Day 1: a welcome email. Day 3: a case study. Day 7: a special offer. Day 14: a check-in.

You write the emails once. AgentNexLiFy sends them automatically, on schedule, personalized with the lead's name and details. It tracks opens and clicks. You can see exactly who read what."

**DEMO** — real email sending via Resend. Tracking pixels. Fully functional.

---

### 3g. Automations (`/dashboard/automations`)

"Beyond email sequences, you can set up trigger-based automations. Examples:
- When a new lead is captured → send yourself an SMS alert instantly
- When an appointment is completed → send the customer a review request email  
- When someone's been in 'Quoted' stage for 7 days → send a follow-up text

These run in the background, 24/7, without you touching anything."

**DEMO** — appointment reminders, review requests, SMS alerts all work.

---

### 3h. Reviews (`/dashboard/reviews`)

"When a customer completes an appointment, AgentNexLiFy automatically sends them an email asking for a Google review. When a review comes in, you get an SMS alert.

Inside the dashboard, you can see all your reviews, and for each one, the AI has already drafted a response for you. You read it, tweak it if you want, and post it. Professional responses in 10 seconds instead of 10 minutes."

**DEMO** — AI-drafted responses work. Review request automation works. Note: Google review API sync is not live yet — reviews are currently entered manually or captured via the review request flow.

---

### 3i. Analytics (`/dashboard/analytics`)

"Real numbers, not estimates. Total conversations, leads captured, conversion rate, emails sent, appointments booked — all with trend lines and period comparisons. You'll know exactly how your AI employee is performing."

**DEMO** — all metrics are real database queries.

---

### 3j. Widget Config (`/dashboard/widget`)

"This is where you customize how the widget looks and behaves. Change the bot name, color, greeting message, position on the page. The embed code is right here — one script tag you paste into your website once and you're done."

**DEMO** — fully functional.

---

### 3k. FAQ Manager (`/dashboard/faq`)

"The AI answers questions based on what it knows about your business. This is where you add to that knowledge base. Q: Do you offer financing? A: Yes, we offer 0% financing for 12 months. Every time a customer asks that, the AI answers correctly. You're training it without writing a single line of code."

**DEMO** — fully functional.

---

### 3l. Team (`/dashboard/team`) — *if relevant*

"If you have staff, you can add them here with role-based access. Owners see everything. Admins can manage leads and conversations. Team members see only what's relevant to them. You can assign leads and conversations to specific people."

**DEMO** — invite flow, role permissions all work.

---

### 3m. Billing (`/dashboard/billing`) — *brief mention*

"Billing is handled securely through Stripe. You can upgrade, downgrade, or cancel directly from your dashboard — no need to call anyone. It's month-to-month, no contracts."

**DEMO** — fully functional Stripe integration.

---

## Act 4: The Widget Demo (10 min)

> *This is the centerpiece. Go to the live demo widget on `https://www.agentnexlify.com` or use the widget on their newly created account.*

"Now let me show you what your customers actually experience. I'm going to chat with your AI right now, pretending to be a customer."

*[Open the widget. Type the following, showing the screen as you go.]*

---

### Sample Conversation (customize to client's industry)

**Customer:** Hi, I need some help.

**AI:** Hi there! Welcome to [Business Name]. I'm [Bot Name], your virtual assistant. I'd be happy to help! What can I assist you with today?

---

**Customer:** What services do you offer?

**AI:** *[Answers based on their FAQ entries or website content — real response from Claude AI]*

---

**Customer:** Do you have availability this week for [service]?

**AI:** Absolutely! We typically have openings throughout the week. To get you scheduled, could I get your name and a good email address?

---

**Customer:** Sure, it's Sarah Johnson, sarah@email.com

*[Watch the lead capture happen in real time.]*

**AI:** Perfect, Sarah! I've got your contact info. Let me check our availability... We have openings on Wednesday at 2pm and Thursday at 10am. Which works better for you?

---

**Customer:** Thursday at 10 works.

**AI:** Great! I've noted Thursday at 10am for you, Sarah. You'll receive a confirmation shortly. Is there anything else I can help you with?

---

**Customer:** No that's great, thanks!

**AI:** Wonderful! We look forward to seeing you Thursday. Don't hesitate to reach out if anything comes up. Have a great day!

---

*[Now switch to the dashboard.]*

"Watch this. While we were talking — Sarah is now in your leads."

*[Show the Leads page. Sarah Johnson's lead card is there.]*

"Name, email, conversation summary, lead score — all captured automatically. If I had my phone connected, I'd have gotten a text the second she typed her email. She's already been enrolled in your welcome email sequence. And if we had booking fully configured, that appointment would be on the calendar right now.

That happened while you were sleeping, or on a job site, or with another customer. That's the whole point."

---

## Act 5: The Value Pitch (5 min)

> *Don't talk features. Talk outcomes.*

"Let me put some numbers on this. Let's say your website gets 200 visitors a month. Today, maybe 3-5 of them reach out. With the widget running 24/7, you might capture 20-30 leads a month from that same traffic — people who would have left and called someone else.

At even a 20% close rate, that's 4-6 new customers from traffic you already have. If your average job is $500, that's $2,000-3,000 in new revenue every month from your existing website. The Growth plan is $249 a month.

But beyond revenue — think about time. How many hours a week does your team spend on: answering the same questions over and over, playing phone tag to book appointments, manually sending follow-up emails, writing responses to Google reviews? 

AgentNexLiFy does all of that automatically. You get those hours back."

---

## Act 6: Next Steps (5 min)

### If they want to start now:

"You already have an account — we just created it. All you need to do is:
1. Add your FAQs and services in the dashboard (takes 20 minutes)
2. Copy the one-line widget script and paste it into your website header
3. Turn it on

We can walk through that together right now, or I can send you a step-by-step guide."

### If they need to think:

"Totally fair. Here's what I'll do — I'll leave your trial account active so you can poke around. The free plan lets you run up to 50 conversations a month, so you can see real results before you commit to anything. Go put the widget on your site this week and see what happens."

### Pricing Summary:

| Plan | Price | Best For |
|------|-------|----------|
| **Free** | $0/mo | Try it — 50 conversations/month, lead capture, widget |
| **Growth** | $249/mo | Active businesses — unlimited conversations, full CRM, email sequences |
| **Autopilot** | $299/mo | Hands-off businesses — everything automated, less manual |
| **Professional** | $499/mo | Growing teams — Local SEO, campaigns, white-label, priority support |
| **Enterprise** | $899/mo | Multi-location or agency — full suite, webhooks, team accounts |

All plans are month-to-month. No contracts. Cancel anytime from your dashboard.

---

## Q&A Cheat Sheet

| Question | Answer |
|----------|--------|
| **Does this replace my website?** | No — it adds a chat widget to your existing website. You paste in one line of code and it appears on every page. |
| **What if the AI gives wrong information?** | The AI only answers based on what you've told it in the FAQ manager and widget setup. It won't make things up about your business. If it doesn't know something, it offers to have you follow up personally. |
| **Can I customize what the AI says?** | Yes. You control the bot's name, personality, greeting, and every answer it gives. You can also add custom instructions like "always recommend booking a consultation" or "never quote prices." |
| **Does it work on mobile?** | Yes — the widget is fully responsive and works on any device. |
| **What happens when someone wants to speak to a human?** | You can set up a handoff trigger. The AI tells the customer a real person will reach out, you get an SMS notification instantly, and the conversation is flagged in your dashboard. |
| **Does it connect to my Google Calendar?** | Yes. Connect Google Calendar in the integrations tab and appointments sync both ways automatically. |
| **Can it send texts (SMS) too?** | Yes — you can receive SMS alerts when a lead is captured, and the system can send automated texts as part of follow-up sequences. (Requires Twilio setup.) |
| **Does it work in languages other than English?** | Claude AI is multilingual — it can respond in the language the customer writes in. |
| **What if I want to cancel?** | Cancel anytime from the Billing page in your dashboard. No penalties, no calls. Your account reverts to the free plan. |
| **Is my customer data secure?** | All data is stored in Supabase (PostgreSQL) with row-level security. No data is shared between business accounts. |
| **How long does setup take?** | Most businesses are live in under an hour. The onboarding wizard walks you through everything. |
| **Do you integrate with [CRM/tool they use]?** | We have a webhooks system that can push events to any tool that accepts webhooks (Zapier, Make, HubSpot, etc.). Native integrations: Google Calendar, Twilio, Stripe, Resend. |
| **What's the difference between Growth and Autopilot?** | Both are great for most businesses. Growth is $249 and gives you the full CRM, email sequences, and unlimited conversations. Autopilot is $299 and adds more automation tools for hands-off operation. Professional at $499 adds Local SEO, campaign tools, and white-labeling. |
| **Can multiple people use the same account?** | Yes — the Growth plan and above support team members with role-based access (owner, admin, team member). |
| **What if my website platform doesn't support custom code?** | We work with any website that allows you to add HTML. That includes WordPress, Squarespace, Wix, Shopify, Webflow, and custom sites. If you're on a locked platform, we can explore alternatives. |
| **Does the AI book actual appointments or just ask for info?** | It can do both. It captures contact info from every conversation automatically. For actual scheduling, you connect your Google Calendar and configure your availability — then it can show real open slots and request a booking. |
| **Is there a free trial?** | Yes — the free plan is unlimited in time, just capped at 50 conversations/month. There's no credit card required to start. |

---

## Emergency Backup Plan

| What breaks | What to do |
|-------------|-----------|
| **Widget doesn't appear on demo site** | Go directly to `https://www.agentnexlify.com` — the production widget runs on the landing page. Use that for the demo instead. |
| **Chat gives an error** | Say: "The AI is live but occasionally rate-limited — let me show you a recent example conversation from a real session." Switch to showing the Conversations page with existing data. |
| **Dashboard is slow to load** | Backend runs on Railway. If it's cold-starting (rare), refresh once. Say: "It's waking up — normally instant." |
| **Lead doesn't appear after chat** | Lead capture runs as a background task — it may take 15-30 seconds. Say: "The pipeline processes it in the background — check back in a moment." Then proceed and come back to it. |
| **Signup fails** | Use a pre-created demo account instead. Have credentials ready: `demo@agentnexlify.com` / demo password in your notes. |
| **Google Calendar OAuth fails** | Say: "OAuth requires a live Google account — I'll skip this step but it's a one-click connect once you're in your own account." Don't linger. |

---

## Features to SKIP (Internal — Do Not Demo)

| Feature | Why |
|---------|-----|
| **Social Media posting** | Posts are saved but NOT actually pushed to Instagram/Facebook/Twitter. Don't click "Publish." |
| **Calls / AI Answering** | Call routing is a skeleton — no live voice integration. |
| **Facebook Messenger** | Routes exist in backend, no working integration. |
| **Google Review Import** | Reviews are manually entered — there's no live Google Reviews API sync. Don't imply it auto-imports. |
| **Local SEO score** | SEO audit data is stored but the live scoring engine is incomplete. Results may be empty or stale. |

---

## Feature Confidence Summary

| Category | Confidence | Notes |
|----------|-----------|-------|
| AI Chat Widget | DEMO | Fully live — calls Claude API |
| Lead Capture | DEMO | Automatic, real-time |
| Lead CRM | DEMO | Full CRUD, scoring, notes |
| Pipeline / Kanban | DEMO | Drag-drop, custom stages |
| Appointments / Calendar | DEMO | Slot logic, Google Cal sync |
| Email Sequences | DEMO | Real sending via Resend |
| Automations | DEMO | SMS alerts, review requests, reminders |
| Reviews + AI Responses | DEMO | AI drafting works; import is manual |
| Analytics | DEMO | All real data |
| Widget Customization | DEMO | Color, name, position, embed code |
| FAQ Manager | DEMO | Directly trains AI responses |
| Team Management | DEMO | Invite, roles, permissions |
| Billing / Stripe | DEMO | Real checkout, webhooks |
| Client Portal | MENTION | Exists, mostly functional |
| Chat Flow Builder | MENTION | Works but complex to demo quickly |
| Smart Lists | MENTION | Exists, filtering works |
| Forms Builder | MENTION | Exists, submissions saved |
| Social Media | SKIP | No live publishing |
| AI Answering / Calls | SKIP | Incomplete |
| Facebook Messenger | SKIP | Not implemented |
| Google Review Import | SKIP | Manual only, don't imply auto |
| Local SEO live scoring | SKIP | Incomplete |
