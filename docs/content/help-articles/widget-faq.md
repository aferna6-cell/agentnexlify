# Widget FAQ — Common Questions

Answers to the most common questions about the AgentNexLiFy chat widget.

---

### How do I add the widget to my website?

Copy your embed code from the dashboard (Widget page or the main dashboard) and paste it before the `</body>` tag on every page of your website. It's one line of code:

```html
<script async src="https://app.agentnexlify.com/widget/agentnexlify-widget.js"
  data-api-key="YOUR_API_KEY"
  data-api-base="https://agentnexlify-production.up.railway.app">
</script>
```

See the full guide: [How to embed the widget](./how-to-embed-the-widget.md)

---

### Can I customize how the widget looks?

Yes. Go to the **Widget** page in your dashboard to change:
- Bot name
- Greeting message
- Primary color (match your brand)
- Position (bottom-right or bottom-left)

---

### Can the widget book appointments?

Yes. Enable booking in the Widget settings, set your hours in the Availability page, and optionally connect Google Calendar. The AI will offer available time slots during conversations.

---

### Does the widget work on mobile?

Yes. The widget is fully responsive and works on all modern browsers, phones, and tablets. On mobile, it opens full-screen for a better chat experience.

---

### What happens when I'm offline?

If you toggle your widget to "Offline" mode, visitors see a contact form instead of the chat. They can leave their name, email, and message. You'll get notified and can follow up later.

---

### Can the widget speak other languages?

Yes. The AI automatically detects the language the visitor uses and responds in the same language. No configuration needed — it works with any language Claude supports (100+ languages).

---

### How does the AI know about my business?

Three ways:
1. **Website scanning** — Add your website URL in Settings, click "Scan Website", and the AI reads your site automatically.
2. **FAQ entries** — Add common questions and answers in the FAQ Manager.
3. **Feedback corrections** — Use the thumbs-down button on bad AI responses and type what it should have said. The AI learns from corrections.

---

### Can my team respond to conversations?

Yes. Invite team members from the Team page. They can:
- View all conversations
- Reply to visitors directly
- Leave internal notes (invisible to visitors)
- Be assigned to specific conversations

---

### Is the widget GDPR compliant?

The widget doesn't use cookies or localStorage for tracking. Conversation data is stored securely in your Supabase database. For GDPR compliance, add a note to your privacy policy about the chat widget collecting name, email, and phone when voluntarily provided by visitors.

---

### Can I see what visitors are saying?

Yes. Go to the **Conversations** page to see every chat in real-time. You can filter by tags, search by content, and click any conversation to read the full transcript.

---

### How do I turn off the widget temporarily?

Go to the Widget page and toggle the "Online" switch off. The widget will show an offline contact form instead of the AI chat. Toggle it back on anytime.

---

### Does the widget slow down my website?

No. The widget script loads asynchronously (`async` attribute) so it never blocks your page from rendering. It's about 50KB — smaller than most images on your site.

---

### Can I use the widget on multiple websites?

Each widget embed code is tied to one business account. If you need widgets for multiple businesses, create a separate AgentNexLiFy account for each one.

---

### What if the AI gives a wrong answer?

Click the thumbs-down button on the message and type the correct answer. The AI will learn from your correction and won't make the same mistake again. You can also add the correct info to your FAQ Manager for immediate improvement.
