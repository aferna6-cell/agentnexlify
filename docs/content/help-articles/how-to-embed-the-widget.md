# How to Embed the Chat Widget on Your Website

Your AgentNexLiFy chat widget is an AI assistant that lives on your website. It greets visitors, answers questions, captures contact info, and books appointments — all automatically.

## Quick Setup (2 minutes)

### 1. Find your embed code

Log in to your [AgentNexLiFy dashboard](https://app.agentnexlify.com). Your embed code is on the main dashboard page under "Widget Setup." It looks like this:

```html
<script
  src="https://app.agentnexlify.com/widget/agentnexlify-widget.js"
  data-api-key="YOUR_API_KEY"
  data-api-base="https://agentnexlify-production.up.railway.app">
</script>
```

### 2. Add it to your website

Paste the embed code just before the closing `</body>` tag on every page where you want the chat widget to appear.

**WordPress:** Go to Appearance > Theme Editor > footer.php, paste before `</body>`

**Wix:** Go to Settings > Custom Code > Add Code, paste in the "Body - end" section

**Squarespace:** Go to Settings > Advanced > Code Injection > Footer, paste the code

**Shopify:** Go to Online Store > Themes > Edit Code > theme.liquid, paste before `</body>`

**HTML site:** Open your HTML file, find `</body>`, paste the code right above it

### 3. That's it

Refresh your website. You should see the chat bubble in the bottom-right corner.

## Customization

You can customize how the widget looks and behaves from your dashboard:

- **Assistant name** — What your AI introduces itself as
- **Greeting message** — The first message visitors see when they open the chat
- **Primary color** — Match your brand colors
- **Position** — Bottom-right or bottom-left
- **Branding** — On paid plans, you can remove the "Powered by AgentNexLiFy" badge

Go to Dashboard > Settings > Widget to make changes. They take effect immediately — no need to update the embed code.

## Troubleshooting

**Widget doesn't appear?**
- Make sure the code is before `</body>`, not inside `<head>`
- Check that your API key is correct (starts with `anx_`)
- Clear your browser cache and refresh

**Widget loads but chat doesn't work?**
- Make sure `data-api-base` points to `https://agentnexlify-production.up.railway.app`
- Check your browser console for CORS errors. If you see one, contact support with your domain name

**Widget looks different than expected?**
- Customization changes apply immediately. Make sure you saved your changes in the dashboard.
- Some website builders add CSS that conflicts with the widget. Try adding `!important` to your widget's primary color in the dashboard.

## FAQ

**Does the widget slow down my website?**
No. The widget script loads asynchronously — it doesn't block your page from rendering.

**Can I put the widget on multiple pages?**
Yes. Use the same embed code on every page. Each visitor gets one continuous conversation regardless of which page they're on.

**Does it work on mobile?**
Yes. The widget is fully responsive and works on phones, tablets, and desktops.

**How do I see the conversations?**
Log in to your dashboard and go to "Conversations." You'll see every chat, the visitor's contact info (if shared), and a lead score.
