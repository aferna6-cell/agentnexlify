# Marketing Copy — /integrations/zapier Landing Page

**Draft status:** v1 — ready for partner review  
**Target URL:** `/integrations/zapier`  
**Target audience:** Home service business owners (plumbers, HVAC, landscapers) on Free tier evaluating upgrade; and Growth/Pro tenants deciding to activate the Zapier integration.  
**Primary CTA:** Upgrade to Growth (Free visitors) / Connect Zapier (existing Growth/Pro)

---

## Hero Section

**Headline:**  
Every lead goes straight to your CRM. Automatically.

**Subheadline:**  
Connect AgentNexLiFy to Jobber, ServiceTitan, Housecall Pro, HubSpot, and 7,000+ other apps — no code, no copy-pasting, no dropped leads.

**CTA (primary):**  
[Upgrade to Growth — $249/mo] 

**CTA (secondary, for logged-in Growth/Pro users):**  
[Connect Zapier in 10 minutes →]

**Supporting line beneath CTA:**  
Available on Growth and Professional plans. Setup takes under 10 minutes.

---

## Social Proof Bar

*[Logo row: Jobber | ServiceTitan | Housecall Pro | HubSpot | Google Sheets | Slack + "+7,000 more apps"]*

---

## Problem/Solution Block

**Problem (left column):**  
You're capturing leads with your chat widget. Then manually copying names, phones, and emails into your CRM. One by one. Every day.

That's 20–40 minutes of data entry for every 10 leads. At 50 leads a month, that's 2+ hours your dispatcher isn't dispatching.

**Solution (right column):**  
AgentNexLiFy's Zapier integration sends every new lead to your CRM within 60 seconds. Name, phone, email, and service interest — all pre-filled. No copy-paste. No missed leads. No lag.

---

## How It Works

**Step 1 — Generate your API key**  
In Settings → Integrations → Zapier, click "Generate API Key." Copy it. 30 seconds.

**Step 2 — Connect in Zapier**  
Search "AgentNexLiFy" in Zapier, select the "New Lead" trigger, paste your key. Zapier tests the connection automatically.

**Step 3 — Pick your CRM**  
Choose Jobber, ServiceTitan, Housecall Pro, or any of 7,000+ apps. Map name → name, phone → phone, service interest → notes. Done.

**Step 4 — Every lead lands in your CRM**  
Widget captures a lead → Zapier fires within 60 seconds → CRM creates the contact record. Your team picks it up from there.

---

## Featured Integrations

### Jobber
Send leads directly to Jobber as new client records. Name, phone, email, and service interest pre-filled. Your team can book a quote from the Jobber mobile app before the lead goes cold.  
[→ See the Jobber setup guide]

### ServiceTitan
Route web chat leads into ServiceTitan's Leads module with correct business unit, campaign attribution, and customer details. Dispatchers see new leads in their queue alongside phone leads.  
[→ See the ServiceTitan setup guide]

### Housecall Pro
Create Housecall Pro customers automatically with lead source set to "Website Chat" for revenue attribution reporting. Tag leads "Chat Lead" for follow-up campaigns.  
[→ See the Housecall Pro setup guide]

### HubSpot, Salesforce, Google Sheets, Slack, and more
Any app in Zapier works with AgentNexLiFy leads. Build multi-step Zaps to notify your team on Slack, log leads to a spreadsheet, and create CRM contacts — all from one trigger.

---

## Key Benefits

**No dropped leads**  
Manual copy-paste means mistakes. Automation means every lead captured by the widget reaches your CRM, every time.

**60-second lead delivery**  
Zapier polls every 1 minute. A lead submitted at 2pm is in your CRM by 2:01pm — while the customer is still thinking about their problem.

**One key, any CRM**  
One API key works with every Zapier app. Switch CRMs? Update one connection in Zapier, not your whole workflow.

**Revoke instantly**  
If a key is ever shared accidentally, revoke it in one click. The Zap stops within 60 seconds. Generate a new key, reconnect, done.

---

## Pricing Callout

**Available on:**  
- Growth ($249/mo) — includes Zapier + 2,500 leads/mo + AI chat + automation  
- Professional ($499/mo) — includes Zapier + unlimited leads + advanced automation + priority support

**Not available on:**  
- Free plan  

[Compare all plans →]

---

## FAQ

**Do I need a paid Zapier account?**  
No — Zapier's free plan supports 2-step Zaps, which covers the AgentNexLiFy → CRM use case. Paid Zapier plans add multi-step Zaps, faster polling (1 min vs 15 min on free), and higher task limits.

**Which CRMs are supported?**  
Any CRM with a Zapier integration — that's 7,000+ apps. We publish step-by-step guides for Jobber, ServiceTitan, and Housecall Pro because those are the most common among our home-service tenants.

**What lead data is sent to my CRM?**  
Name, email, phone, service interest (what the customer said they need), and the timestamp the lead was captured. Payment information and conversation transcripts are never included.

**Is my API key secure?**  
Yes. AgentNexLiFy stores only a cryptographic hash of your key — not the key itself. If you need to revoke a key (e.g., it was shared accidentally), you can do so instantly from Settings → Integrations → Zapier.

**Does this work with my existing Zaps?**  
Yes. The API key can be used across multiple Zaps. We recommend using a separate named key per Zap so you can revoke or audit them independently.

---

## Bottom CTA

**Ready to stop copy-pasting leads?**  
Connect AgentNexLiFy to your CRM in 10 minutes.

[Upgrade to Growth — $249/mo]  
[See all integrations →]

---

## Notes for Design/Dev Implementation

- Hero background: dark, consistent with dashboard aesthetic.
- CRM logos in the social proof bar should be official brand logos (check each vendor's logo usage policy before publishing).
- "How It Works" section: consider a 4-step animated/illustrated flow.
- The Jobber/ServiceTitan/HCP cards link to their respective KB articles (`/knowledge-base/wiki/integrations/zapier-jobber.md`, etc.) — these should render as help docs, not marketing pages.
- "Compare all plans" link targets `/pricing`.
- FAQ should use an accordion component for mobile.
- A/B test headline: "Every lead goes straight to your CRM" vs "Stop copy-pasting leads. Connect to Jobber in 10 minutes."
