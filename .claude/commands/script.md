---
description: Generate a client-ready demo script from working features. Use when prepping a sales demo or walkthrough.
model: sonnet
---

Generate a client-ready demo script based on the current state of the codebase. The script should only reference features that actually work right now.

## Step 1: Discover What's Actually Built

Don't guess. Verify each feature by reading the code:

**Signup/Auth:**
- Read the signup route — does it work? What fields does it collect?
- Read the login route — does it work?
- What does the onboarding flow look like after signup?

**Dashboard:**
- List every page/route in the dashboard
- For each page: what does it show? Does it have data? Does it handle empty state?

**Chat Widget:**
- How is it embedded? (script tag, iframe, etc.)
- What can it do? (answer questions, book appointments, capture leads)
- Read the system prompt configuration — what does the AI know about?
- Is there a demo widget on the landing page?

**Lead Capture:**
- What info does it extract? (name, email, phone, anything else?)
- Where does it show up in the dashboard?
- Is there a lead pipeline/kanban view?

**Appointments:**
- Can users book through the chat?
- Is there a calendar view?
- What fields does an appointment have?

**Analytics:**
- What metrics are shown?
- Does it have real data or just empty state?

**Integrations:**
- SMS (Twilio) — configured and working?
- Google Calendar — configured and working?
- Webhooks — endpoint exists? Test button works?
- Stripe billing — configured and working?

**Business Page:**
- Does /biz/{slug} work?
- What does it show?

**Other:**
- Team members / multi-user?
- White-label / branding?
- Automated follow-ups?
- Any other features you discover?

## Step 2: Categorize Confidence

For each feature, assign a confidence level:

- **DEMO** — fully working, safe to show a client
- **MENTION** — exists but untested or partially working, mention verbally but don't deep-dive
- **SKIP** — broken, empty, or not ready, don't bring it up

## Step 3: Determine the Client Type

Check if I specified a business type (e.g., "/script restaurant" or "/script plumber"). If I did, tailor the entire script to that business. If I didn't, write a generic version with placeholder notes for customization.

## Step 4: Generate the Demo Script

Write a complete, ready-to-use demo script with this structure:

### Pre-Demo Checklist
- [ ] items based on what needs to be verified before the meeting
- [ ] include: is Supabase paused? Is backend running? Is frontend deployed?

### Act 1: The Problem (2 min)
Opening pitch tailored to the client type. Frame the pain point that AgentNexLiFy solves for THEIR specific business.

### Act 2: Sign Up Together (5 min)
Walk through the actual signup flow based on what the signup page currently collects. Use the client's real business name.

### Act 3: Dashboard Tour (5 min)
Walk through only the pages that are in DEMO confidence. For each page, include:
- What to click
- What to say
- What the client will see (based on empty state since it's a new account)

### Act 4: The Widget Demo (10 min)
This is the main event. Write a realistic sample conversation tailored to the client's business type. Include:
- 5-7 message exchanges
- At least one where the customer gives their name and email (to demo lead capture)
- At least one where they ask about booking (to demo appointments, if working)
- After the conversation: switch to dashboard and show the lead appearing

### Act 5: The Value Pitch (5 min)
Key talking points tailored to the client type. Focus on outcomes not features.

### Act 6: Next Steps (5 min)
- If they want to start: what to do
- If they need to think: what to leave them with
- Pricing overview based on current pricing tiers

### Q&A Cheat Sheet
A table of likely questions and answers, tailored to what's actually true about the product right now. Don't promise features that aren't built.

### Emergency Backup Plan
What to do if specific things break during the demo, based on known fragile areas.

### Features to SKIP (internal note)
List features that are broken or not ready, so the presenter knows what to avoid.

## Step 5: Save the Script

Save to docs/content/demo-scripts/demo-script-[date].md

If a client type was specified, save as demo-script-[client-type]-[date].md

Print a brief summary of what was generated and the confidence breakdown (how many features are DEMO vs MENTION vs SKIP).
