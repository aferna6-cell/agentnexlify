# Competitive Research — March 2026

Analyzed: Intercom, Drift, Tidio, LiveChat, Crisp, Freshchat, HubSpot, GoHighLevel.
Focus: Features that matter to small business owners, feasible with our stack.

## Strategic Finding

AgentNexLiFy is feature-complete for small business operations. The gap is engagement and stickiness — features that make businesses say "I can't run without this."

## 8 New Feature Ideas (Priority Order)

### 1. Canned Response Auto-Suggest
**Inspired by:** Intercom, Freshchat, Crisp
**Why it matters:** Team types 2 chars, sees "We're open 9-5" auto-suggested because the conversation just asked about hours. Cuts response time in half.
**What to build:** Claude scores snippets by relevance on debounced keyup. Top 3 shown as autocomplete dropdown. Click to insert.
**Effort:** Low | **Impact:** Medium

### 2. Custom Lead Fields
**Inspired by:** HubSpot, GoHighLevel
**Why it matters:** A plumber needs "pipe type". A contractor needs "project size". Generic fields don't cut it. Custom fields make the CRM feel built for their business.
**What to build:** Settings page to define custom fields (text, dropdown, date). JSONB storage on leads. Auto-extract from conversation via Claude. Filter/export by custom fields.
**Effort:** Medium | **Impact:** High

### 3. CSAT/NPS Surveys
**Inspired by:** Freshchat, Intercom, LiveChat
**Why it matters:** One-click satisfaction rating after every interaction. Identifies unhappy customers for follow-up.
**What to build:** After conversation resolved, auto-send 1-5 rating via email/SMS. Dashboard CSAT trends card. Webhook event for Zapier.
**Effort:** Low | **Impact:** Medium

### 4. Live Visitor Behavior Tracking
**Inspired by:** Drift, Intercom
**Why it matters:** "They've been on the pricing page for 4 minutes" — triggers proactive chat. Converts more visitors.
**What to build:** Widget JS tracks page URL, time on page, scroll depth. Expose to AI system prompt. Dashboard "Live visitors" count.
**Effort:** Medium | **Impact:** Medium

### 5. Smart Team Routing Rules
**Inspired by:** GoHighLevel, Drift, Freshchat
**Why it matters:** Auto-route conversations by skill tags, availability, or round-robin. Reduces manual assignment overhead.
**What to build:** Settings rule editor. Pre-built: round-robin, online-only, skill-based. Fallback to owner.
**Effort:** Medium | **Impact:** Medium

### 6. Pre-Chat Forms
**Inspired by:** Intercom, Freshchat, Tidio
**Why it matters:** Collect structured info before conversation starts. Saves AI from asking name/phone/service every time.
**What to build:** Form node type in visual flow builder. Drag-and-drop fields. Data auto-populated into chat context.
**Effort:** Medium | **Impact:** High

### 7. Public Knowledge Base
**Inspired by:** All competitors
**Why it matters:** Self-serve help articles reduce support load AND build SEO value. Auto-suggest articles in chat.
**What to build:** Article CRUD in settings. Public page at /help/{tenant-slug}. Widget suggests articles before chat. Search.
**Effort:** Medium | **Impact:** Medium

### 8. Email Inbox Integration
**Inspired by:** Freshchat, Intercom
**Why it matters:** Service businesses get questions via email. Should be in the same inbox as chat + SMS.
**What to build:** Gmail/Outlook OAuth. Sync emails into conversations table. Reply from dashboard. Thread by sender.
**Effort:** High | **Impact:** High

## Implementation Roadmap

1. Canned Response Auto-Suggest (quick win, 1 week)
2. Custom Lead Fields (medium, 2 weeks, highest perceived value)
3. CSAT/NPS Surveys (quick, 1 week)
4. Live Visitor Behavior Tracking (medium, 2 weeks)
5. Smart Team Routing Rules (medium, 2 weeks)
6. Pre-Chat Forms (medium, adds to flow builder)
7. Public Knowledge Base (medium, SEO value)
8. Email Inbox Integration (large, high impact for service businesses)

## Competitive Moat

Ship these 8 and the pitch becomes: "We're the AI platform built for small businesses. Not a sales tool (Drift), not a phone system, not a CRM with a widget tacked on (HubSpot). We're a unified operating system: AI chat + CRM + automations + phone + bidding + reviews + hiring. Custom fields say 'we built this for your industry.' Smart routing says 'we handle distribution, you handle strategy.'"
