---
name: widget-test
description: Test, debug, or verify the chat widget covering load, conversation, data capture, cross-origin behavior, and file sync. Use when user says 'widget test', 'test widget', 'widget debugging', 'widget checklist', 'chat widget test', or asks about widget test.
version: 1.1.0
origin: claude
triggers:
- widget test
- test widget
- widget debugging
- widget checklist
- chat widget test
paths: widget/**,frontend/public/widget/**,backend/routers/widget_*.py,backend/routers/widget_*_helpers.py
when_to_use: After editing widget JS, widget routers, or chat API. After changing lead capture or conversation storage. When a tenant reports the widget isn't working cross-origin.
effort: low
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

### Lead Enrichment (if `enable_structured_lead_parser = true`)
- [ ] After message containing contact info, `activity_log` has a `lead_enriched` row within ~2s
- [ ] `metadata.fields_added` lists the fields the extractor filled that regex missed
- [ ] Lead row has populated `name`, `email`, `phone`, `areas_of_interest` where applicable
```sql
SELECT metadata->>'fields_added', lead_id, created_at
FROM activity_log
WHERE activity_type = 'lead_enriched' AND tenant_id = '<tenant_id>'
ORDER BY created_at DESC LIMIT 5;
```

### Cross-Origin (CRITICAL)
- [ ] Works on different domain — no CORS errors
- [ ] Check main.py CORS allowlist includes the domain

### File Sync (CRITICAL)
- [ ] widget/agentnexlify-widget.js matches frontend/public/widget/agentnexlify-widget.js
- [ ] Both files are identical byte-for-byte

## Gotchas

| Symptom | Cause | Fix |
|---------|-------|-----|
| Widget doesn't load | Script URL wrong | Check embed code |
| "Sorry I am having trouble connecting" | CORS preflight 400 on 3rd-party domain | Hard-code `allow_origins=["*"]` in `backend/main.py` — the dynamic `_cors_origins()` regresses (fd24b43, 9b07a59) |
| No lead created | Leads query uses `tenant_id` not `client_id` | Run schema-guard. Leads table column is `client_id`, unique across the entire codebase |
| No conversation memory | Session ID not persisting | Browser storage quirk — test incognito |
| `widget/` and `frontend/public/widget/` drift | Edit skipped one copy | Must be identical byte-for-byte. Pre-push hook checks this |
| Widget sends messages but inbox empty | Orphan chat_messages — missing conversation row | `INSERT ... ON CONFLICT DO NOTHING` on conversations before inserting messages |
| RLS enabled, no policies → silent zero-row writes | Service role key not used OR anon key + missing policy | 120/146 MTOptions sessions failed this way. Check `pg_policies` for the target table |

After fixing, update docs/dev-knowledge/bug-patterns.md.
