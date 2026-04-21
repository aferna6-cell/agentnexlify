# Power Washing Demo — Setup Guide

Local-only demo for the power washing prospect meeting. Zero prod DB writes.

---

## Prerequisites

- Local Supabase running (`supabase start` via Supabase CLI, or Docker stack)
- Backend running on port 8000
- `SUPABASE_URL` pointing at local instance (e.g., `http://localhost:54321`)
- `SUPABASE_SERVICE_KEY` set to local anon/service key
- Python venv activated

---

## Step 1 — Run the seed script

From the project root:

```bash
python scripts/demos/seed_powerwash_demo.py
```

The script prints the `api_key` at the end. Copy it.

If it says `ABORT: SUPABASE_URL points at the production database` — stop and fix your `.env` to point at local Supabase before proceeding.

---

## Step 2 — Start the backend

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

---

## Step 3 — Create a throwaway HTML test page

Save this as `/tmp/powerwash-demo.html` and open it in your browser:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Clean Slate Power Washing</title>
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }
    h1 { color: #1E90FF; }
  </style>
</head>
<body>
  <h1>Clean Slate Power Washing</h1>
  <p>Professional exterior cleaning for homes and businesses in Springfield.</p>
  <p>Services: house washing, driveway cleaning, deck restoration, roof soft wash, gutters, commercial.</p>
  <p>Call us at 555-867-5309 or chat below for a free estimate.</p>

  <!-- AgentNexLiFy widget — replace YOUR_API_KEY with the key from seed output -->
  <script
    src="http://localhost:8000/widget/agentnexlify-widget.js"
    data-api-key="YOUR_API_KEY"
    data-api-base="http://localhost:8000"
    data-brand-color="#1E90FF">
  </script>
</body>
</html>
```

Replace `YOUR_API_KEY` with the `api_key` printed by the seed script.

---

## Meeting Demo Flow

### What to click / show

1. **Open the chat widget** — click the blue chat bubble in the bottom-right corner.
   - Shows the greeting from "Wade" (the demo bot name).

2. **Ask a pricing question** — type: `How much does a house wash cost?`
   - Bot answers with price ranges and pushes toward a free estimate.
   - Demonstrates FAQ routing and AI response.

3. **Trigger lead capture** — type: `I want to get a quote for my driveway`
   - Bot should ask for your name and contact info.
   - After providing name + email, a lead entry is created in the DB.

4. **Check the lead in the dashboard** (open `http://localhost:3001` in another tab)
   - Navigate to Leads — the demo lead should appear with `client_id` set to the demo tenant.
   - Shows the live lead capture loop end to end.

5. **Ask an objection question** — type: `Can I just rent a pressure washer myself?`
   - Bot handles the objection using the KB copy.

6. **Ask a services question** — type: `Do you do roof cleaning?`
   - Bot explains soft wash vs pressure wash, demonstrating knowledge depth.

---

### What NOT to click during the meeting

- **Appointments / booking flow** — calendar integration is not configured on the demo tenant. Clicking "Book appointment" may return an error or empty calendar.
- **Email/SMS notifications** — demo tenant uses a fake email (`demo-powerwash@agentnexlify-demo.local`). Real notification triggers will fail silently or error in logs.
- **Dashboard billing page** — demo tenant has no Stripe customer ID. The billing page will show an error.
- **Managed Agents tab** — not configured for the demo tenant.
- **Any "Send test email" button** — fake email domain will bounce.

---

## Cleanup After the Meeting

The demo tenant only exists locally. If you want to remove it:

```bash
# Connect to local Supabase SQL editor or run:
# DELETE FROM tenants WHERE owner_email = 'demo-powerwash@agentnexlify-demo.local';
# Cascades to widget_configs, business_hours, faq_entries, leads automatically.
```

---

## Before a Real Go-Live with This Client

1. Open `widget/knowledge-bases/powerwash-demo_kb.md`
2. Replace every `[TODO: client]` flag with the real business data
3. Update the seed script or manually update the `widget_configs.knowledge_base` column
4. Set a real `owner_email`, phone, and city in the tenant row
5. Configure a real notification email in the dashboard
6. Run the widget-test skill checklist (`.claude/skills/widget-test/SKILL.md`)
