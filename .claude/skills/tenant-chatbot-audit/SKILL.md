---
name: tenant-chatbot-audit
description: "Audit a specific tenant chatbot for data gaps, RLS failures, FAQ quality, orphaned sessions, and knowledge base issues."
version: 1.0.0
origin: claude
user_invocable: true
triggers: ["tenant chatbot audit", "chatbot audit", "bot audit", "tenant bot not working", "leads not capturing", "chatbot diagnosis"]
---

# Tenant Chatbot Audit

Deep diagnostic for a specific tenant's chatbot. Use when: bot isn't working, leads aren't capturing, client complaints about response quality.

## Usage

- `/tenant-chatbot-audit <tenant_id>` — full audit
- `/tenant-chatbot-audit <business_name>` — lookup by name first

## When to Use
- A specific tenant's chatbot is malfunctioning or not capturing leads
- A client reports problems with their chatbot's response quality
- Diagnosing RLS failures, orphaned sessions, or FAQ quality issues for a tenant

## When NOT to Use
- System-wide chatbot issues (debug directly without tenant focus)
- General codebase security review (use security-audit instead)
- Schema validation across all tables (use schema-guard instead)

## Audit Steps

### 1. Pull Tenant Config

```sql
SELECT id, business_name, business_type, plan, owner_email
FROM tenants WHERE id = '<tenant_id>';

SELECT bot_name, greeting_message, booking_enabled, is_online,
       custom_instructions, branding
FROM widget_configs WHERE tenant_id = '<tenant_id>';
```

If `is_online = false`, flag immediately — widget is disabled.

### 2. Check RLS Policies (CRITICAL)

This is the #1 silent killer. RLS enabled + no policies = all anon INSERTs silently fail.

```sql
-- Check if RLS is enabled on key tables
SELECT relname, relrowsecurity
FROM pg_class
WHERE relname IN ('chat_messages', 'conversations', 'leads', 'appointments');

-- Check what policies exist
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE tablename IN ('chat_messages', 'conversations', 'leads', 'appointments');
```

If RLS is enabled but no policies exist for `anon` or `service_role`, the widget cannot write data. Fix: add appropriate policies or use service_role key.

### 3. Check Recent Chat Sessions

```sql
-- Last 20 sessions
SELECT session_id, COUNT(*) as msg_count,
       MIN(created_at) as started, MAX(created_at) as last_msg
FROM chat_messages
WHERE tenant_id = '<tenant_id>'
GROUP BY session_id
ORDER BY last_msg DESC
LIMIT 20;
```

Red flags:
- Zero sessions = widget not connecting or RLS blocking
- Sessions with only 1 message = bot not responding
- All sessions < 2 messages = greeting works but AI fails

### 4. Check for Orphaned Sessions

Sessions in `chat_messages` with no matching `conversations` row:

```sql
SELECT cm.session_id, COUNT(*) as msgs
FROM chat_messages cm
LEFT JOIN conversations c ON cm.session_id = c.session_id AND c.client_id = '<tenant_id>'
WHERE cm.tenant_id = '<tenant_id>'
AND c.id IS NULL
GROUP BY cm.session_id;
```

Orphaned sessions = leads never captured from those conversations.

### 5. Check FAQ Quality

```sql
SELECT id, question, answer, category
FROM faq_entries WHERE tenant_id = '<tenant_id>'
ORDER BY category;
```

Check for:
- Zero FAQs = bot has no domain knowledge
- Contradictory answers (same topic, different info)
- Leakage from other tenants (FAQ referencing wrong business name)
- Missing categories (hours, services, pricing, location, contact)

### 6. Check Knowledge Base

```sql
SELECT url, crawl_status, pages_found, extracted_text IS NOT NULL as has_text
FROM website_content WHERE tenant_id = '<tenant_id>';
```

If `extracted_text` is NULL or `crawl_status != 'completed'`, the AI has no website context.

### 7. Check Lead Capture

```sql
SELECT COUNT(*) as total_leads,
       COUNT(CASE WHEN created_at > now() - interval '7 days' THEN 1 END) as last_week
FROM leads WHERE client_id = '<tenant_id>';
```

Compare lead count vs session count. Big gap = lead extraction failing.

### 8. Check for Spam/Junk

```sql
SELECT content, LENGTH(content) as len
FROM chat_messages
WHERE tenant_id = '<tenant_id>' AND role = 'user'
AND (LENGTH(content) < 3 OR content ~ '^(.)\1+$')
ORDER BY created_at DESC LIMIT 20;
```

## Report

Write to stdout:

```
## Tenant Chatbot Audit — <business_name> (<tenant_id>)

### Status: 🔴 BROKEN / 🟡 DEGRADED / 🟢 HEALTHY

### Findings
1. [CRITICAL/HIGH/MEDIUM/LOW] Description
2. ...

### Data Summary
- Sessions (7d): N
- Leads (7d): N
- Orphaned sessions: N
- FAQ entries: N
- Knowledge base: populated/empty
- RLS policies: present/MISSING

### Recommended Fixes
1. ...
```

## Fix Process

Fix in order: RLS policies → orphaned session backfill → FAQ/KB gaps → code-level issues.
