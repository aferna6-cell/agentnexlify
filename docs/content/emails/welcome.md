# Welcome Email — New Signup

**Subject:** Welcome to AgentNexLiFy — let's get your first lead

**From:** AgentNexLiFy <noreply@agentnexlify.com>
**Trigger:** Immediately after successful registration

---

Hi {{owner_name}},

Welcome to AgentNexLiFy! You just gave {{business_name}} a 24/7 AI assistant that captures leads, books appointments, and follows up automatically.

Here's how to start getting leads in the next 10 minutes:

**Step 1: Embed your chat widget**
Copy this code and paste it before the `</body>` tag on your website:

```html
<script
  src="https://agentnexlify.vercel.app/widget/agentnexlify-widget.js"
  data-api-key="{{api_key}}"
  data-api-base="https://agentnexlify-production.up.railway.app">
</script>
```

That's it. Your widget is live.

**Step 2: Customize your assistant**
Go to your dashboard and set up:
- Your assistant's name and greeting message
- Your business hours (so it can book appointments)
- Your FAQ answers (so it sounds like you)

**Step 3: Watch the leads come in**
Every visitor who shares their name, email, or phone number through the chat becomes a lead in your dashboard. You'll see their conversation, contact info, and a lead score that tells you who's ready to buy.

**Your 14-day free trial is active.** You have full access to everything — no credit card needed.

Questions? Just reply to this email.

— The AgentNexLiFy Team

---

**Template variables:**
- `{{owner_name}}` — from RegisterRequest.owner_name
- `{{business_name}}` — from RegisterRequest.business_name
- `{{api_key}}` — generated on signup (anx_... format)
