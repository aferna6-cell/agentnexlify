# Test Results
_Track what features have been tested, what passed, what failed._

## 2026-03-23

### Build Tests
- Backend import: PASS (`from backend.main import app`)
- Frontend build: PASS (`npm run build` in 5.06s)

### Code Audit Results
- `from __future__ import annotations`: 0 occurrences (PASS)
- `except BaseException`: 0 occurrences (PASS)
- `leads.tenant_id`: 0 occurrences (PASS)
- `conversations.tenant_id` (query context): 0 remaining after fix (PASS)
- Route shadowing: 0 remaining after fix (PASS)
- Claude model IDs: all claude-sonnet-4-6 (PASS)
- Widget JS sync: files identical (PASS)
- Anthropic client timeout: all have explicit timeout (PASS)
- CORS configuration: wildcard origins correctly set (PASS)

### Features Not Tested (need live environment)
- Recurring invoice generation (needs paid recurring invoice in DB)
- Conversation search (needs chat messages in DB)
- Bulk lead actions (needs leads in DB)
- No-show detection (needs confirmed appointment past start time)
