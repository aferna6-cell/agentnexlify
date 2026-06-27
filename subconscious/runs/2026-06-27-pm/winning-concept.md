# Run 70 Winner: AI-to-Human Handoff v1

**Date:** 2026-06-27-pm
**Run:** 70
**Category:** customer_value
**Confidence:** HIGH
**Effort:** M (~1 day, reduced from 1.5-2d by os_outbound_mirror.py)
**Autonomous:** No — human required
**Moratorium override:** No — recommendation only

---

## Mandate Executed: Widget Drift Retired

Before this winner: **run_70_mandate fires.**

`check_project_invariants.py` still exits 1 at run 70 (6th consecutive failure).
Widget drift topic retired from subconscious permanently.

Actions taken:
1. Written: `docs/reminders/widget-drift-URGENT.md` — 30-second fix command
2. Push notification sent (URGENT)
3. Topic added to `retired_topics` in governance.json — will not appear in subconscious again

Human fix (30 seconds):
```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
python3 scripts/check_project_invariants.py
git add landing-page-v2/widget/agentnexlify-widget.js
git commit -m "fix: sync widget to landing-page-v2 mirror (widget drift — run 70 mandate)"
```

---

## Winner: AI-to-Human Handoff v1

### Why This, Why Now

- **72 days pending** (run 4, 2026-04-16). Oldest direction in governance.
- **Critical gap for all 7 industries** — customer-gaps.md lists it as highest-priority unimplemented feature.
- **Infrastructure ready**: `os_outbound_mirror.py` merged PR #188 (2026-05-27, 152 tests) — SMS + email outbound delivery available.
- **Scope shrunk**: run 4 estimated 1.5-2 days. With os_outbound_mirror.py, delivery layer is built — ~1 day remaining.
- **Widget drift retired**: no competitor for the winner slot. First clean winner choice in 6 runs.
- **Council sprint velocity**: 9 commits in 4 days proves development is active.

### What to Build

When a widget chat user sends a trigger phrase ("talk to a person", "real person", "human agent", "speak to someone", "transfer me"), the system should:

1. **Detect trigger** in `backend/routers/widget_chat.py` — after AI generates a response, check if user message matches trigger pattern (regex or exact-match list).
2. **Write handoff_requests row** — new table `handoff_requests(id, client_id, conversation_id, trigger_phrase, status, created_at, notified_at)`.
3. **Notify owner** — call `os_outbound_mirror.py` with SMS + email to tenant owner: "A customer is requesting to speak with a human. Conversation: {link}. Lead: {name/phone if known}."
4. **Acknowledge in chat** — widget response: "I've notified the team. Someone will follow up with you shortly."
5. **Dashboard indicator** — badge count on ConversationsPage sidebar for unresolved handoff requests.

### Files to Touch

| File | Change |
|------|--------|
| `migrations/155_handoff_requests.sql` | CREATE TABLE handoff_requests |
| `backend/routers/widget_chat.py` | detect trigger phrase, call handoff_service |
| `backend/services/handoff_service.py` | new file — trigger detection, DB write, outbound notify |
| `backend/tests/test_handoff_service.py` | new file — trigger detection tests, DB write tests, notify tests |
| `frontend/src/pages/ConversationsPage.jsx` | handoff badge on sidebar |
| `frontend/src/utils/api/conversations.js` | add `getHandoffRequests()` API call |

Widget JS change (optional v1 scope — defer to v2):
- "Request Human" button could be added to widget UI
- v1 scope: server-side trigger detection only (no widget button)

### Migration

```sql
-- migrations/155_handoff_requests.sql
CREATE TABLE handoff_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    trigger_phrase TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'notified', 'resolved')),
    notified_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: client_id scoped (follows widget_configs pattern)
ALTER TABLE handoff_requests ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant isolation" ON handoff_requests
    USING (client_id = (SELECT client_id FROM auth_context()));

CREATE INDEX idx_handoff_requests_client_status ON handoff_requests(client_id, status);
CREATE INDEX idx_handoff_requests_conversation ON handoff_requests(conversation_id);
```

### Trigger Detection Logic

```python
HANDOFF_TRIGGERS = [
    "talk to a person", "real person", "human agent",
    "speak to someone", "transfer me", "speak with a human",
    "real human", "talk to someone", "connect me with",
    "need a person", "want a person",
]

def detect_handoff_trigger(user_message: str) -> bool:
    msg_lower = user_message.lower()
    return any(t in msg_lower for t in HANDOFF_TRIGGERS)
```

### os_outbound_mirror.py Integration

The delivery layer is ready. Confirm interface before calling:
```bash
grep -n "def send\|async def" backend/services/os_outbound_mirror.py | head -20
```

Expected call pattern (verify against actual interface):
```python
from backend.services.os_outbound_mirror import OutboundMirror

await OutboundMirror.send(
    client_id=client_id,
    channel="sms",
    to=owner_phone,
    message=f"Customer requested human handoff. Conversation: {conversation_link}",
)
```

### Tests Required

- `test_handoff_trigger_detection`: verifies each trigger phrase matched, non-triggers not matched
- `test_handoff_request_created_on_trigger`: widget_chat route writes handoff_requests row on trigger
- `test_no_handoff_on_normal_message`: non-trigger messages don't write handoff rows
- `test_owner_notified_via_outbound_mirror`: outbound call dispatched (mock os_outbound_mirror)
- `test_dashboard_handoff_count`: `GET /api/handoffs/pending` returns correct count per client_id

### Invariants (from CLAUDE.md)

- Use `client_id` NOT `tenant_id` on `handoff_requests` table
- No `from __future__ import annotations` in any FastAPI file
- Migration numbered 155 (confirm next number before writing SQL)
- Widget JS changes require byte-identical sync — v1 defers widget button to avoid sync requirement

---

## Bonus A: Plan-Name Invariant Guard Check 7

AUTONOMOUS-EXECUTABLE after widget drift fix.

Add `foundation` and `operations` to retired plan names in `check_project_invariants.py`:
```python
RETIRED_PLAN_NAMES = ["foundation", "operations"]  # add if not already present
```

Sequencing: human fixes widget drift → nightly runs this autonomously → moratorium exit path continues.

## Bonus B: SMS Compliance Dashboard

After AI-to-Human Handoff v1 lands. Backend already has TCPA opt-out suppression (council Fix #1, 9ddfd0e).
Dashboard component `SMSComplianceCard.jsx` shows opt-out count, last opt-out timestamp, suppressed/sent ratio.
S-M effort. Route to nightly or next council sprint.

---

## RUN 71 MANDATE

If AI-to-Human Handoff v1 is still `status: pending_approval` in run 71 (no implementation started):
- Provide implementation sketch as copy-paste code blocks for the 3 core files
- Flag as longest-pending direction in governance (73+ days)
- Consider moratorium override if true_pending estimate drops below max_pending_approvals
