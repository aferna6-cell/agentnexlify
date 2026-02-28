# AgentNexLiFy Chat Widget

A lightweight, embeddable AI chat widget that adds a live chat experience to any website. Zero dependencies, Shadow DOM isolated, works on all modern browsers.

## Quick Start

Paste this single line before your closing `</body>` tag:

```html
<script
  src="https://agentnexlify.com/widget/nexlify-chat.js"
  data-business-id="YOUR_BUSINESS_ID"
  data-business-name="Your Business Name">
</script>
```

That's it. A floating chat bubble will appear in the bottom-right corner of your site.

## Configuration

All configuration is done via `data-` attributes on the script tag:

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `data-business-id` | Yes | `"demo"` | Your unique business ID (provided in your dashboard) |
| `data-business-name` | No | `"Us"` | Displayed in the chat header |
| `data-primary-color` | No | `#00bfff` | Accent color for the bubble and user messages |
| `data-position` | No | `"right"` | Chat bubble position: `"right"` or `"left"` |
| `data-greeting` | No | `"Hi there! How can I help you today?"` | Initial bot message |
| `data-webhook-url` | No | — | URL to POST lead data to when captured |

### Example with all options:

```html
<script
  src="https://agentnexlify.com/widget/nexlify-chat.js"
  data-business-id="acme-plumbing-123"
  data-business-name="Acme Plumbing"
  data-primary-color="#e74c3c"
  data-position="right"
  data-greeting="Welcome to Acme Plumbing! Need a quote or have a question?"
  data-webhook-url="https://your-api.com/webhooks/leads">
</script>
```

## Features

- **Floating chat bubble** with smooth open/close animations
- **Dark theme** chat window (380x520px on desktop, fullscreen on mobile)
- **Keyword-aware responses** that handle greetings, pricing, hours, services, and more
- **Lead capture flow** — automatically collects name, email, and phone after 2 messages
- **Session persistence** — chat history survives page refreshes (sessionStorage)
- **Shadow DOM isolation** — widget CSS never conflicts with your site
- **Mobile responsive** — fullscreen chat on screens under 768px
- **Typing indicator** — animated dots while "thinking"
- **Unread badge** — notification count on the bubble when chat is closed
- **Accessible** — ARIA roles, keyboard navigation, focus management

## Lead Capture

After 2+ user messages, the widget prompts for contact info (name, email, phone). Captured leads are:

1. Logged to `console.log` (for development)
2. POSTed to your `data-webhook-url` (if configured) as JSON:
   ```json
   {
     "businessId": "your-id",
     "name": "Jane Doe",
     "email": "jane@example.com",
     "phone": "555-1234",
     "timestamp": "2026-02-27T12:00:00.000Z",
     "source": "https://yoursite.com/page"
   }
   ```
3. Stored in `localStorage` under `nexlify_leads_[businessId]` as a fallback

## Free Tier Limits

- Unlimited widget loads
- Keyword-based responses (demo/simulation mode)
- Lead capture with localStorage + webhook support
- "Powered by AgentNexLiFy" watermark

## Upgrading

Upgrade to a paid plan to unlock:

- **Custom AI training** — train the bot on your business data
- **Remove watermark** — white-label the widget
- **Analytics dashboard** — track conversations, leads, and conversion rates
- **CRM integrations** — auto-sync leads to HubSpot, Salesforce, etc.
- **Custom styling** — full theme control beyond accent color

Visit [agentnexlify.com/pricing](https://agentnexlify.com/pricing) to upgrade.

## File Structure

```
widget/
├── nexlify-chat.js        # Production-minified (embed this)
├── nexlify-chat.src.js    # Readable source version
├── demo.html              # Demo page (fake business site)
└── README.md              # This file
```

## Browser Support

Chrome 60+, Firefox 63+, Safari 12+, Edge 79+

## Size

~14KB minified (no gzip). Zero external dependencies.
