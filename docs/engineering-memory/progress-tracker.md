# Progress Tracker
_What was built each session. Proves velocity, prevents re-doing work._

## 2026-03-23 Session

### Bugs Fixed (Phase A)
1. **conversations.client_id regression #3** — Fixed 8 locations across sms.py (2), analytics.py (4), services/conversation.py (2)
2. **Route shadowing** — Fixed documents.py (templates unreachable) and webhooks.py (schema/events unreachable)
3. **NULL plan defaults** — Fixed 23 occurrences of `.get("plan", "free")` pattern across 6 files
4. **NULL business_name defaults** — Fixed 13 occurrences across 6 files
5. **Silent except blocks** — Added logging to 2 silent fallbacks in sequences.py
6. Total: 48 individual code fixes across 13 files

### Features Built (Phase B)
1. **Recurring invoice auto-generation** (automation_engine.py + main.py)
   - Processes paid recurring invoices where next_invoice_date <= today
   - Clones items/amounts, generates sequential number, advances date
   - Activity log dedup, webhook fire, 4 interval types
2. **Conversation search** (conversation_inbox.py + inbox.js + ConversationsPage.jsx)
   - Full-text search via ilike on chat_messages
   - Snippet extraction with context around match
   - Enriched with lead names, conversation tags
   - Frontend: debounced server search with results overlay
3. **Bulk lead actions** (leads.py + leads.js + LeadsPage.jsx)
   - Checkbox selection on LeadTable with select-all
   - 4 actions: assign, change_status, add_tag, delete
   - Bulk action bar with dynamic parameter inputs
   - Max 200 leads per batch
4. **Appointment no-show detection** (automation_engine.py + analytics.py + main.py)
   - Auto-marks confirmed appointments as no_show after 30 min past start
   - No-show analytics endpoint with rate calculation + repeat offenders
   - Activity log entries for dashboard visibility

### Backlog
- Added 15 new backlog items (waitlist, timeline, bulk actions, webhook retry, etc.)
- Updated bug-patterns.md with 3 new entries
