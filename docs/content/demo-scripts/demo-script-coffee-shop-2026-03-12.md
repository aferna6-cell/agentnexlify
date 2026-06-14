# AgentNexLiFy Demo Script — Coffee Shop
**Date generated:** 2026-03-12
**Client type:** Coffee shop / cafe
**Duration:** ~30 minutes
**Confidence breakdown:** 22 DEMO / 5 MENTION / 3 SKIP

---

## Feature Confidence Matrix

| Feature | Level | Notes |
|---------|-------|-------|
| Signup / Login | DEMO | Full flow, collects business name, industry, city, owner name |
| Dashboard overview | DEMO | Onboarding checklist, stats cards, lead pipeline, activity feed |
| Chat widget | DEMO | Live AI conversation, lead capture, multi-language |
| Lead capture (auto) | DEMO | Extracts name, email, phone, auto-tags |
| Lead pipeline / table | DEMO | Kanban + table views, drag-drop stages |
| Lead import (CSV) | DEMO | Upload with dedup, max 500 rows |
| Lead merge / dedup | DEMO | Duplicate detection by email/phone |
| Quick email follow-up | DEMO | Inline compose from lead drawer |
| Conversations view | DEMO | Chat history, tagging, transcript export |
| Appointment booking | DEMO | Through widget, calendar view, recurring |
| Calendar | DEMO | Week/day views, status tracking |
| Availability config | DEMO | Business hours, timezone, slot duration |
| Analytics | DEMO | Conversation trends, lead stages, peak hours |
| Widget customization | DEMO | Colors, bot name, greeting, branding, online/offline toggle |
| FAQ manager | DEMO | Add Q&A for the AI to reference |
| Business page (/biz/) | DEMO | Hosted page with widget embedded |
| Reviews dashboard | DEMO | Add reviews, AI draft responses, analytics |
| Email templates | DEMO | 6 starter templates, custom builder |
| Settings | DEMO | Business info, SMS toggle, review request config |
| Billing / pricing | DEMO | Plan cards, trial status, Stripe checkout |
| Team management | DEMO | Invite members, assign roles |
| Webhooks | DEMO | Create, test, view delivery logs |
| Google Calendar | MENTION | OAuth flow exists, needs Google credentials configured |
| Automation sequences | MENTION | Builder exists, execution engine needs cron setup |
| SMS notifications | MENTION | Twilio integration built, needs phone number configured |
| Missed call text-back | MENTION | Webhook endpoint built, needs Twilio number |
| Offline widget mode | MENTION | Works but better to demo online mode |
| Widget file upload | SKIP | Endpoint exists but UI incomplete |
| Direct GBP posting | SKIP | OAuth not connected, future feature |
| Bulk SMS campaigns | SKIP | Not built yet |

---

## Pre-Demo Checklist

- [ ] Backend running at api.agentnexlify.com (check: `curl https://api.agentnexlify.com/health`)
- [ ] Frontend deployed on Vercel (check: visit https://agentnexlify.com)
- [ ] Supabase project is NOT paused (free tier pauses after 7 days inactivity)
- [ ] Create a test account with their business name BEFORE the demo (so there's some data)
- [ ] Have 2-3 test conversations in the widget so the dashboard isn't empty
- [ ] Have the widget embed page open in a separate tab
- [ ] Have their Google Maps / Yelp page open to show where reviews come from
- [ ] Close all unrelated browser tabs
- [ ] Test the demo widget on the landing page loads correctly
- [ ] Disable notifications on your machine

---

## Act 1: The Problem (2 min)

> "Let me ask you something — what happens when someone messages your coffee shop at 10pm asking about catering for an office event? Or when someone walks by, checks your Google listing, and has a question about your seasonal menu?
>
> Right now, that customer either calls and gets voicemail, sends an email that sits in your inbox until morning, or just... moves on to the next shop.
>
> That's not a marketing problem. You didn't lose them because your coffee isn't good. You lost them because nobody was there to answer.
>
> AgentNexLiFy puts an AI assistant on your website — and your Google Business page — that knows your menu, your hours, your catering options, everything. It answers questions, captures their contact info, and books appointments. 24/7. While you're pulling shots or closing up for the night.
>
> Let me show you exactly how it works."

---

## Act 2: Sign Up Together (5 min)

> "Let's set this up for your shop right now. It takes about 60 seconds."

**Walk through signup at `/signup`:**

1. **Business name:** "Brewed Awakening" (use their real name)
2. **Industry:** "Restaurant / Cafe"
3. **City:** [their city]
4. **Owner name:** [their name]
5. **Email:** [their email]
6. **Password:** [let them choose]

> "That's it. You're in. No credit card, no setup fee. You get a 7-day free trial with everything unlocked."

**After signup, you'll land on the Dashboard.**

> "This is your command center. Right now it's fresh — let's fill it up."

---

## Act 3: Dashboard Tour (5 min)

**Dashboard Home:**
> "You'll see your onboarding checklist here — it walks you through getting set up. You've got your stats at the top: conversations today, leads captured, appointments booked, and your current plan.
>
> Down here is your lead pipeline — when customers start chatting with your AI, their info shows up here automatically. You can drag them between stages: new, contacted, appointment booked, closed."

**Widget Page (click "Widget" in sidebar):**
> "This is where you customize your AI assistant. Let's make it feel like YOUR shop."

1. Change **bot name** to "Brewed Bot" (or their preference)
2. Change **greeting** to: "Hey! Welcome to Brewed Awakening. Ask me about our menu, hours, catering, or anything else!"
3. Set **primary color** to their brand color (brown/warm tone for a coffee shop)
4. Show the **embed code**: "This one line of code goes on your website. Copy, paste, done."

**FAQ Manager (click "FAQs" in sidebar):**
> "This is the secret sauce. You add your common questions here, and the AI uses them to give accurate answers."

Add 3 quick FAQs:
- **Q:** "Do you have oat milk?" **A:** "Yes! We have oat, almond, and coconut milk. No extra charge for alt milks."
- **Q:** "Do you do catering?" **A:** "Absolutely! We cater office events, meetings, and private parties. We do coffee bars with a barista, pastry platters, and custom drink menus. Minimum order is 15 people."
- **Q:** "What are your hours?" **A:** "Monday-Friday 6am-6pm, Saturday-Sunday 7am-4pm. We're in downtown [city]."

> "Now your AI knows these answers. Let's test it."

---

## Act 4: The Widget Demo (10 min)

> "I'm going to pretend I'm a customer visiting your website. Watch what happens."

**Open the widget** (either on the business page at `/biz/{slug}` or from the embed preview).

### Sample Conversation

**Customer (you type):**
> "Hi! Do you guys do catering for corporate events?"

**AI will respond** something like:
> "Hey there! Yes, we absolutely do corporate catering! We offer coffee bars with a barista on-site, pastry platters, and custom drink menus. Our minimum order is for 15 people. What kind of event are you planning?"

**Customer:**
> "We're doing a team retreat next month, about 40 people. We'd love a coffee bar setup. What does that cost?"

**AI will respond** with catering info and will naturally try to collect contact details.

**Customer:**
> "That sounds great. My name is Sarah Chen and my email is sarah@techstartup.com. Can someone call me to discuss the details?"

**AI will respond** confirming the info and offering to book a time to talk.

**Customer:**
> "Sure, do you have anything available next Tuesday afternoon?"

**AI will respond** with available time slots (if availability is configured).

**Customer:**
> "2pm works. My phone is 864-555-0123."

**AI will confirm** the booking.

---

**NOW — switch to the dashboard.**

> "Watch this. Let's go to Leads."

**Click "Leads" in sidebar.**

> "See? Sarah Chen is already here. Email, phone, everything she gave us. The AI automatically pulled it from the conversation. No form. No friction. She just... talked.
>
> And look at these tags — [point to auto-generated tags like 'catering', 'corporate event', '40 people']. The AI tagged this lead so you know exactly what she wants without reading the whole conversation."

**Click on Sarah's lead to open the detail drawer.**

> "Here's everything: her contact info, the conversation transcript, her lead score. And look — you can send her a follow-up email right from here."

**Show the email compose in the drawer.**

> "Type a quick note: 'Hi Sarah, thanks for your interest in our catering! I'd love to chat about your team retreat. Looking forward to Tuesday at 2pm.' Hit send. Done. Her status automatically moves to 'contacted.'"

**Click "Calendar" in sidebar.**

> "And there's the appointment. Tuesday at 2pm. Sarah Chen, catering consultation. If you connect Google Calendar, this syncs automatically."

**Click "Conversations" in sidebar.**

> "Here's the full conversation transcript. You can tag it, export it, whatever you need."

---

## Act 5: The Value Pitch (5 min)

> "Let's talk about what this means for a coffee shop like yours.
>
> **The after-hours problem is solved.** Someone Googles you at 9pm and wants to know about catering? Your AI handles it. No missed leads.
>
> **Catering inquiries convert better.** Instead of 'fill out this form and we'll get back to you,' it's a real conversation. The AI asks the right questions, captures all the details, and books the meeting. That's the difference between a $2,000 catering order and a lost lead.
>
> **You stop answering the same questions.** 'What are your hours?' 'Do you have wifi?' 'Where are you located?' Your AI handles all of that while you focus on making coffee.
>
> **You know who your customers are.** Every conversation becomes a lead in your pipeline. Tags tell you what they want. Scores tell you who's serious. You can send follow-up emails, set up appointment reminders, even request Google reviews after a catering event.
>
> **It speaks any language.** If a customer messages in Spanish, the AI responds in Spanish. No configuration needed.
>
> And here's the thing — this costs less than one shift of a part-time employee. And it never calls in sick."

---

## Act 6: Next Steps (5 min)

### If they want to start:

> "You're already set up! Here's what to do next:
>
> 1. **Add your FAQs** — spend 15 minutes adding your top 10 questions. Menu items, hours, catering details, parking, wifi password, whatever people ask.
> 2. **Set your business hours** in Settings so the AI knows your schedule.
> 3. **Embed the widget** — copy that one line of code to your website. If you don't have a website, we give you a hosted business page at agentnexlify.com/biz/brewed-awakening.
> 4. **You're live.** Start capturing leads tonight."

### If they need to think:

> "Totally understand. Your free trial runs for 7 days — everything is unlocked right now. Play with it. Send the widget link to a friend and have them test it. See how it handles real questions about your business.
>
> I'll follow up in a few days to see how it's going."

### Pricing overview:

> "Quick pricing breakdown:
>
> - **Free** — $0/month. AI chat widget, lead capture, unlimited conversations during your 7-day trial. Great for testing.
> - **Growth** — $199/month. Everything in Free plus: custom branding, email sequences, appointment booking, SMS notifications, white-label widget.
> - **Professional** — $399/month. Everything in Growth plus: Google Calendar sync, team members, advanced analytics, custom CSS, business page SEO.
> - **Enterprise** — $799/month. Everything in Professional plus: priority support, API access, custom integrations.
>
> For a coffee shop doing catering, Growth is the sweet spot. You get appointment booking, follow-up emails, and your branding on the widget. No setup fees."

---

## Q&A Cheat Sheet

| Question | Answer |
|----------|--------|
| "Can it take food orders?" | "The AI can discuss your menu and guide people on how to order, but it doesn't process payments or submit orders to your POS. It's focused on answering questions, capturing leads, and booking appointments — like catering consultations or event planning calls." |
| "What if the AI says something wrong?" | "It only knows what you tell it through your FAQs and business info. You control the knowledge base. Plus you can see every conversation in your dashboard and correct course if needed." |
| "Does it work with my website?" | "Yes — it's one line of code. Works on Squarespace, Wix, WordPress, Shopify, custom sites, anything. If you don't have a website, we give you a hosted page." |
| "Can my employees see the leads?" | "Yes. You can invite team members with different roles — admin, member, or viewer. Everyone sees the same dashboard." |
| "What about Google reviews?" | "We just launched a reviews feature. You can manage all your reviews from the dashboard and use AI to draft professional responses. We can also auto-send review requests after catering events." |
| "Is there a contract?" | "No contracts. Month-to-month. Cancel anytime from the billing page." |
| "What happens after the free trial?" | "You stay on the free plan with basic features. To keep appointment booking, email follow-ups, and branding, you'd upgrade to Growth at $199/month." |
| "Do you integrate with Square / Toast?" | "Not yet for POS integration. We do integrate with Google Calendar, Stripe for payments, and we have webhooks so you can connect to Zapier for custom workflows." |
| "Can it handle multiple languages?" | "Yes, automatically. If someone messages in Spanish, French, or any language, the AI responds in that language. No setup needed." |
| "What if I'm closed and someone chats?" | "The AI works 24/7 regardless of your hours. It knows your schedule and will tell visitors when you're open. You can also toggle 'offline mode' which shows a contact form instead of the AI chat." |

---

## Emergency Backup Plan

| If this breaks... | Do this instead... |
|---|---|
| Widget doesn't load | Show the widget preview on the Widget customization page — it renders a live preview right there |
| Chat API is slow (Claude API latency) | "Let me refresh — sometimes the AI takes a moment on the first message." If still slow: "The AI is thinking through a detailed response. In production this averages 2-3 seconds." |
| Supabase is paused | The entire backend will 500. Check before the demo! `curl https://api.agentnexlify.com/health`. If paused, log into Supabase dashboard and unpause (takes ~1 min). |
| Lead doesn't appear immediately | "Lead extraction runs in the background — give it 10-15 seconds." Refresh the leads page. |
| Appointment slots don't show | Availability hasn't been configured. Go to Settings > Availability and set business hours first. |
| Stripe checkout fails | Skip live checkout. Show the billing page and pricing cards instead. "The upgrade is one click when you're ready." |
| Google Calendar OAuth fails | Don't demo it live. Say "Google Calendar sync is available on the Professional plan. You connect it from the Integrations page." |

---

## Features to SKIP (internal — do not mention)

- **Widget file/image upload** — endpoint exists but UI is incomplete
- **Bulk SMS campaigns** — not built yet
- **Google Business Profile direct posting** — no OAuth connected
- **Zapier integration** — webhooks work but no published Zap templates
- **Automation sequence execution** — builder works, but the cron job to process scheduled steps isn't running yet. Don't promise automated email sequences will fire on their own.
- **Missed call text-back** — webhook endpoint exists but requires Twilio phone number provisioning. Don't demo unless a number is configured.
- **Content Studio / Local SEO / Job Board / other new modules** — backlog only, not built
