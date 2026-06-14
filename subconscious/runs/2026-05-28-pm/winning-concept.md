# Winning Concept — 2026-05-28-pm (Run 38)

## Recommendation

Implement AI-to-Human Handoff v1 using the Agent OS outbound infrastructure shipped in PR #188 — detect explicit handoff triggers in `widget_chat.py`, write to a `handoff_requests` table, and dispatch owner notification via `os_outbound_mirror` (SMS/email already working with 152 tests).

---

## Why This, Why Now

PR #188 (Agent OS rehaul, merged 2026-05-27) changes the implementation equation for AI-to-Human Handoff. `os_outbound_mirror.py` now handles SMS, email, and Facebook outbound with replay protection — the delivery layer that previously didn't exist. Before PR #188, handoff required ~3 days of plumbing work. After PR #188, the integration is a routing decision (~1 day): detect trigger in `widget_chat.py` → write to DB → call `os_outbound_mirror.send_sms()`. The feature has been the oldest pending customer-value item (run 4, 42 days, Critical in all 7 industries) and the infrastructure finally makes it a tractable sprint.

The human just demonstrated capacity for M-effort feature sprints by shipping Agent OS Groups A+B+C. The window is open. Customer-gaps.md marks this Critical and it is the only cross-industry gap that hasn't been closed. GoHighLevel's "AI Employee" has human handoff — this is a competitive blind spot.

---

## Implementation Sketch

### Prerequisites
- GH #181 fix (~15 min): add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `billing.py:263-279`; remove backwards assertions in `test_billing_amount_to_plan.py:38-44`
- Review `os_outbound_mirror.py` interface (know the function signatures before writing the hook)

### Step 1 — Trigger detection in widget_chat.py

File: `backend/routers/widget_chat.py`

Add handoff phrase detection before the standard LLM reply path. Trigger strings (explicit only — v1 avoids false positives):
- "talk to someone", "talk to a person", "real person"
- "call me", "phone me", "reach me"
- "need a human", "speak to a human", "human agent"
- "transfer me", "escalate"

Return immediately on match — don't send to LLM.

### Step 2 — handoff_requests table (new migration)

File: `migrations/131_handoff_requests.sql`

```sql
CREATE TABLE handoff_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES tenants(id),
    conversation_id UUID REFERENCES conversations(id),
    lead_id UUID REFERENCES leads(id),
    trigger_phrase TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending, notified, resolved
    notified_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_handoff_requests_client_id ON handoff_requests(client_id);
CREATE INDEX idx_handoff_requests_status ON handoff_requests(status, created_at);
```

Apply via `mcp__supabase__apply_migration`.

### Step 3 — Owner notification via os_outbound_mirror

File: `backend/services/handoff_service.py` (new file, new concern)

```python
from backend.services.os_outbound_mirror import OsOutboundMirror

async def notify_owner_of_handoff(
    client_id: str, 
    conversation_id: str,
    lead_name: str,
    trigger_phrase: str,
    db
) -> None:
    """Write handoff request and notify business owner via SMS or email."""
    # 1. Write to handoff_requests
    # 2. Fetch tenant notification prefs (phone vs email)
    # 3. Call os_outbound_mirror — no new plumbing needed
    mirror = OsOutboundMirror(db=db)
    await mirror.send_owner_notification(
        client_id=client_id,
        message=f"New handoff request from {lead_name}: '{trigger_phrase}'. Open AgentNexLiFy to respond.",
        channel="sms"  # fallback to email if no phone on file
    )
```

Note: Check `os_outbound_mirror.py` for the actual method signatures — adapt to the interface as shipped.

### Step 4 — Widget acknowledgment

In `widget_chat.py`, after calling `notify_owner_of_handoff()`, return a static response to the widget:
> "I'm connecting you with the team now. You'll hear from someone shortly — is there anything else you'd like me to note for them?"

Store this as a `system` message in `conversations` with `role='handoff'` for audit trail.

### Step 5 — Lead status update

Update the lead's `status` to `'needs_follow_up'` (uses the existing `status` column — no schema change needed).

### Step 6 — Tests

File: `backend/tests/test_handoff.py`

Test cases:
- Trigger phrase detected → handoff_request row created
- Non-trigger phrase → normal LLM path continues
- Owner notified via mock of os_outbound_mirror
- Lead status updated to `needs_follow_up`
- Widget receives acknowledgment message

### Step 7 — Commit

```bash
git add migrations/131_handoff_requests.sql backend/services/handoff_service.py backend/routers/widget_chat.py backend/tests/test_handoff.py
git commit -m "feat(widget): AI-to-human handoff v1 — trigger detection + owner notification via os_outbound_mirror"
```

---

## Bonus Action — Do First (3 minutes)

**billing-constant-guard Check 11** (run 37 winner, still unimplemented):

1. Open `scripts/hooks/pre-commit`
2. Copy the 10-line bash block from `subconscious/runs/2026-05-28/winning-concept.md §Step 1`
3. Paste before the final `exit 0`
4. `git add scripts/hooks/pre-commit && git commit -m "guard(billing): add pre-commit Check 11 — billing constant sentinel (WARNING)"`

Total time: 3 minutes. Do this before the handoff sprint.

---

## Standing Actions (Unchanged)

1. **GH #181 billing fix (~15 min):** prerequisite for handoff sprint (see Prerequisites above)
2. **email_sequences.py split (~2h, run 35 winner):** invoke `/god-class-splitter email_sequences.py` after GH #181 fixed
3. **Moratorium Sprint Items A/B/D (~40 min):** check_project_invariants pre-commit Check 10, widget sync guard, CI eval workflow — invoke `/moratorium-sprint`
4. **post-split-test-repair SKILL.md (~5 min):** create `.claude/skills/post-split-test-repair/SKILL.md`

---

## What This Replaces

Previous active direction was billing-constant-guard pre-commit Check 11 (run 37 winner, pending_approval). That item is downgraded to Bonus Action in this run — it remains valid and should be done first, but is not the strategic focus.

---

## Confidence

**MEDIUM** — Agent OS infrastructure genuinely reduces scope (3 days → ~1 day). But AI-to-Human Handoff has appeared in 7 prior run contexts without implementation; the historical conversion rate is low. MEDIUM reflects the real tension between compelling evidence and poor prior implementation rate. If stable post-Agent OS and sprint bandwidth is confirmed, this should be run 39's first action.
