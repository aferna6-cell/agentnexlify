# AgentNexLiFy — Demo Platform

Interactive demo platform showcasing the AgentNexLiFy product suite. Designed for partner and client presentations.

## Quick Start

```bash
cd ~/agentnexlify/demo-platform
npm start
# Opens at http://localhost:3000
```

That's it. The start script installs dependencies and launches both frontend and backend.

## Optional: Enable Live AI Chat

By default, the chatbot uses simulated responses. To connect to a real AI backend:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
npm start
```

The chat page will show "Connected to AI backend" when the API key is active.

## Pages

| Page | What It Demonstrates |
|------|---------------------|
| **Dashboard** | Client operations view — stats, lead pipeline, activity feed, weekly chart |
| **Live Chat** | AI chatbot with real-time lead intelligence extraction panel |
| **FAQ Bot** | AI FAQ support bot with keyword matching and stats tracking |
| **Automations** | 6 interactive automation simulations (missed call text-back, review requests, drip campaigns, etc.) |
| **Notifications** | Real-time notification feed grouped by time |

## Demo Talking Points

### Dashboard
- "This is what your client sees every morning — their entire business in one view"
- "The lead pipeline updates in real-time as the AI captures and qualifies leads"
- "Every automation that fires shows up in the activity feed"

### Live Chat
- "Watch the right panel — as the visitor chats, the AI is extracting their info in real-time"
- "Lead scoring updates live — from Cold to Warm to Hot based on intent signals"
- "See how the automations fire automatically — CRM entry, owner notification, follow-up scheduling"

### FAQ Bot
- "This handles the questions that eat up 30+ minutes of your team's day"
- "Each FAQ answered saves ~3 minutes of human time"
- "When it can't answer, it gracefully escalates and still captures the lead"

### Automations
- "Click Simulate on any card to see exactly how the automation works step-by-step"
- "The missed call text-back alone recovers 47 calls per month for this business"
- "Invoice follow-up reduced collection time from 34 days to 8 days"

### Notifications
- "Every automation, every lead, every touchpoint — all in one feed"
- "Hot leads get instant alerts so the business never misses a high-intent prospect"

## Tech Stack

- **Frontend:** React (Vite)
- **Backend:** FastAPI (Python) — optional, for live AI chat
- **AI:** Anthropic Claude (via API)
- **Database:** None needed — all demo data is in-memory

## Development

```bash
# Frontend only (simulated chat)
npm run dev

# Backend only
cd server && python3 app.py

# Both (recommended)
npm start
```
