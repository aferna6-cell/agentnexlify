# Winning Concept — 2026-05-17 (Run 21)

## Recommendation

Create a GitHub issue with a full implementation sketch for AI-to-Human Handoff v1 — the
31-day critical cross-industry gap that infrastructure already supports — as a parallel track
explicitly authorized by run 20, breaking the meta-fix loop and providing a concrete sprint entry
point for the highest-ROI pending item in the backlog.

---

## Why This, Why Now

**Parallel track explicitly authorized.** Run 20 improvement-backlog.md states: "AI-to-Human Handoff
v1 (run 4, day 30) — Sprint allocation required. Cannot be S-effort auto-implemented. [URGENT —
oldest pending, Critical cross-industry gap, parallel track independent of moratorium]." This is
not a moratorium violation — the governing document for run 21 explicitly approves it.

**Meta loop stalled for 7 consecutive runs.** Runs 15–20 followed moratorium protocol faithfully
(S-effort items and governance escalations as winners). Zero implementations resulted. The protocol
was designed to prevent governance failures; a 7-run deadlock IS the governance failure. Adapting
to the highest-ROI customer value item is the appropriate response.

**Infrastructure exists — no schema work required.** Conversations table stores the full chat context.
Twilio is wired for SMS/voice notification. Resend is wired for email. The implementation is a
new API endpoint, state enum, and notification handlers — no new dependencies or migrations needed
(beyond a status column on conversations, if one doesn't exist).

**This is the business-value breakout the moratorium was protecting against losing.** All 7 industry
verticals list AI-to-Human Handoff as CRITICAL in customer-gaps.md. It's the feature most likely
to improve trial-to-paid conversion across the entire customer base.

**P0 governance mandate from run 20 is honored inside the implementation.** The GH issue should
be labeled P0 and reference the moratorium context — this satisfies the run 20 mandate to escalate
the backlog, while directing that escalation energy toward a customer-value sprint rather than
another governance artifact.

---

## Implementation Sketch

### Step 0: Confirm infrastructure (~5 min)
Check that these are present before writing the issue:
- `conversations` table: confirm `status` column exists or note that a migration is needed
- `backend/routers/conversations.py`: confirm POST /api/conversations/{id}/handoff endpoint
  doesn't already exist (if it does, check completeness)
- `backend/services/twilio_service.py`: confirm SMS send function exists
- `backend/services/resend_service.py` (or equivalent): confirm email send function exists

### Step 1: Create GH Issue (~15 min)

**Title:** `[P0] AI-to-Human Handoff v1 — Explicit Trigger (Run 4, Day 31)`

**Labels:** `customer-value`, `medium-effort`, `p0`, `moratorium-parallel-track`

**Body:**

```markdown
## Context
Subconscious run 4 recommendation (2026-04-16) — 31 days pending. customer-gaps.md: CRITICAL gap,
all 7 industry verticals. Infrastructure already exists. Explicitly authorized as parallel track
in subconscious run 20 backlog.

## Feature: AI-to-Human Handoff (Explicit Trigger, v1)

When a user explicitly requests to speak to a human (or the tenant enables auto-escalation for
complex queries), the widget conversation state transitions to "awaiting_human" and the tenant
receives a notification via SMS (Twilio) or email (Resend) with the conversation context.

## Scope (v1 — explicit trigger only)

**In scope:**
- Explicit trigger: user says "speak to someone", "talk to a human", "human please"
- Widget state machine: transitions conversation.status "active" → "awaiting_human"
- Tenant notification: Twilio SMS + Resend email with conversation summary
- Dashboard indicator: "Awaiting Human" queue visible in dashboard

**Out of scope for v1:**
- Automatic escalation based on sentiment/topic (v2)
- Real-time chat between human agent and widget user (v3)
- SLA tracking or queue assignment (v4)

## Implementation

### 1. Migration (if status column missing)
```sql
-- Only if conversations.status doesn't already exist
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'active';
```

### 2. Backend: POST /api/conversations/{id}/handoff
```python
# backend/routers/conversations.py
@router.post("/{conversation_id}/handoff")
async def request_human_handoff(
    conversation_id: str,
    client_id: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Verify conversation belongs to client_id
    # 2. Set conversations.status = 'awaiting_human'
    # 3. Fetch conversation history (last 10 messages)
    # 4. Send Twilio SMS to tenant's phone_number
    # 5. Send Resend email to tenant's email
    # 6. Return updated conversation
```

### 3. Widget trigger detection
In widget JS: detect explicit handoff phrases in user message:
```javascript
const HANDOFF_PHRASES = [
  'speak to', 'talk to a human', 'human please', 'real person',
  'agent please', 'representative', 'someone please'
];
```
When detected: call POST /api/conversations/{id}/handoff.

### 4. Dashboard: "Awaiting Handoff" queue
In LeadsPage.jsx or new HandoffPage.jsx: filter conversations WHERE status = 'awaiting_human'.
Show conversation summary + "Mark Handled" button (sets status back to 'resolved').

### 5. Notification templates
SMS: "New handoff request from {lead_name}: \"{last_message}\". View: {dashboard_url}/conversations/{id}"
Email: Subject "Handoff needed — {lead_name}", body includes last 5 messages.

## Acceptance Criteria
- [ ] User message matching HANDOFF_PHRASES triggers conversation.status = 'awaiting_human'
- [ ] Tenant receives SMS within 30 seconds of trigger
- [ ] Tenant receives email within 60 seconds of trigger
- [ ] Dashboard shows "Awaiting Handoff" queue with conversation summary
- [ ] "Mark Handled" sets status to 'resolved'
- [ ] Widget shows "Connecting you with someone from our team..." after trigger

## Files expected to change
- `backend/routers/conversations.py` — new handoff endpoint
- `backend/services/twilio_service.py` — handoff SMS send
- `backend/services/resend_service.py` — handoff email send
- `widget/agentnexlify-widget.js` — phrase detection + status update
- `frontend/public/widget/agentnexlify-widget.js` — byte-identical copy
- `frontend/src/pages/LeadsPage.jsx` or new HandoffPage.jsx — queue view
- `migrations/NNN_conversations_status.sql` — if status column missing

## Estimate
~1.5 days. Backend: 4-5 hours. Widget: 2 hours. Frontend: 2-3 hours. Tests: 2-3 hours.

---

*Subconscious moratorium context: 6 recommendations pending (oldest: 31 days). S-effort exit
path (~50 min): runs 7+8+14+19. See subconscious/runs/2026-05-16-pm/winning-concept.md.
This issue is the parallel track — critical customer value, independent of S-effort moratorium.*
```

---

## What This Replaces

Run 20's governance escalation recommendation (reduce max_pending_approvals 3→2 + GH milestone).
That recommendation remains valid for the moratorium S-effort items and is preserved as a note
inside the GH issue body. The primary winner pivots to customer value — the meta escalation has been
running for 4 consecutive recommendations without producing implementations.

---

## After Run 21 Implemented — Next Run (Run 22)

**If GH issue created + any progress on AI-to-Human Handoff:**
- Run 22 winner: resume moratorium exit sprint (first post-AI-Handoff recommendation)
- Consider: Wire check_project_invariants.py to pre-commit (5 min, run 8) as S-effort parallel action

**If run 21 NOT implemented by run 22:**
- Governance stall is now at the customer-value layer. This signals the human is not engaging
  with subconscious recommendations at all.
- Run 22 governance action: Restart autopilot-issue-loop.yml (confirm it's configured, add
  `ai-ready` label to runs 7+8+14 issues, let autonomous loop handle S-effort items).
- Recommendation: Tag runs 7+8+14 GH issues as `ai-ready` + restart loop.

**Moratorium governance update (run 22):**
- max_pending_approvals: recommend reducing to 2 (run 20 mandate still unfulfilled)
- If loop restarted + S-effort items implemented autonomously: moratorium exits automatically

---

## Confidence

**MEDIUM** — Evidence for the feature's value is HIGH (31 days, CRITICAL gap, all 7 industries,
infrastructure exists). Confidence penalty for moratorium protocol deviation, partially offset by
explicit parallel-track authorization in run 20 backlog. Debate outcome: Idea 2 SURVIVES,
Idea 1 WEAKENED (honored inside this recommendation), Idea 3 KILLED (loop dormant confirmed).
