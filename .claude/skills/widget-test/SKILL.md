---
name: widget-test
description: "Test, debug, or verify the chat widget covering load, conversation, data capture, cross-origin behavior, and file sync."
version: 1.0.0
origin: claude
triggers: ["widget test", "test widget", "widget debugging", "widget checklist", "chat widget test"]
---

# Widget Test

## When to Use
- After any change to the widget or chat API
- After any change to lead capture or conversation storage
- When a customer reports the widget isn't working

## When NOT to Use
- Backend-only changes with no widget interaction
- Dashboard frontend changes unrelated to the widget
- Non-widget-related bug fixes

## Test Checklist

### Widget Loads
- [ ] Script loads without JS errors
- [ ] Widget renders and opens on click
- [ ] Correct tenant branding appears (data-api-key, data-brand-color, data-api-base)

### Conversation Works
- [ ] First message gets AI response
- [ ] Conversation maintains context across messages
- [ ] Session ID persists within same visit

### Data Capture
- [ ] Conversation saved to chat_messages table (canonical store)
- [ ] Name/email/phone creates a lead with correct client_id
- [ ] Lead appears in dashboard

### Cross-Origin (CRITICAL)
- [ ] Works on different domain — no CORS errors
- [ ] Check main.py CORS allowlist includes the domain

### File Sync (CRITICAL)
- [ ] widget/agentnexlify-widget.js matches frontend/public/widget/agentnexlify-widget.js
- [ ] Both files are identical byte-for-byte

## Common Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| Widget doesn't load | Script URL wrong | Check embed code |
| Chat fails | CORS blocking | Add origin to allowlist in main.py |
| No lead created | Schema mismatch (tenant_id vs client_id) | Run schema-guard |
| No conversation memory | Session ID not persisting | Check session management |
| Widget works locally but not externally | CORS config missing domain | Add domain to CORS origins |

After fixing, update docs/dev-knowledge/bug-patterns.md.
