# Run 93 Winning Concept — 2026-07-14

## Winner: connector_awareness.py Cross-Tenant Isolation Test

### Why This Won

Three factors make this the highest-impact action for run 93:

1. **Direct bug evidence from 3 days ago**: commit 7a9047f (2026-07-11) fixed `connector_awareness.py` on the same day it shipped (45401ec) — connect prompt was firing for dashboard threads with `source='chat'`. This is a filtering gap bug. The same class of filtering gap causes cross-tenant data leakage.

2. **Pattern proven in run 53**: `os_action_dispatch.py` had the same profile (behavior tests only, no isolation tests). Subconscious flagged it → nightly implemented isolation test → test caught a regression before production. Direct precedent.

3. **AUTONOMOUS-EXECUTABLE today**: Pure test file. No production code change. No human approval needed. Nightly-commit-review implements in the next cycle without blocking on GH #399, #403, #413, or #415.

### Evidence

- commit 45401ec (2026-07-11): `connector_awareness.py` — 208L service, 370 tests
- commit 7a9047f (2026-07-11, SAME DAY): bug — connect prompt fired for `source='chat'` threads (wrong dimension filter)
- 370 existing tests: cover behavior (does prompt fire?) but NOT isolation (does it ONLY fire for the right tenant?)
- connector_awareness prompt includes tenant-specific connector data (which integrations are connected)
- Cross-tenant connector prompt leak = Tenant A's integration context visible in Tenant B's session

### Pattern Break

Runs 88-92 all targeted `customer_value` (booking diagnostic, referral activation, booking escalation). 5 consecutive runs, 0 human action on the recommendations. Run 93 switches to `code_health` — a domain where the subconscious CAN act autonomously without waiting for human response.

### Implementation Sketch

**File**: `backend/tests/test_connector_awareness_isolation.py`

```python
import pytest
from backend.services.connector_awareness import build_connector_prompt  # adjust import path

def test_connector_prompt_does_not_leak_cross_tenant(db_session, two_tenants_with_connectors):
    """
    Verifies connector_awareness never includes Tenant B's data in Tenant A's prompt.
    Guards against the class of bug in 7a9047f (wrong-dimension filtering).
    """
    tenant_a_id, tenant_b_id = two_tenants_with_connectors

    prompt_a = build_connector_prompt(client_id=tenant_a_id, db=db_session)
    prompt_b = build_connector_prompt(client_id=tenant_b_id, db=db_session)

    # Tenant A's prompt should contain no reference to Tenant B's connector slugs/names
    assert tenant_b_id not in prompt_a, "Tenant B's client_id leaked into Tenant A's connector prompt"
    # Tenant B's prompt should contain no reference to Tenant A's connector slugs/names
    assert tenant_a_id not in prompt_b, "Tenant A's client_id leaked into Tenant B's connector prompt"

def test_connector_prompt_excludes_chat_source_threads(db_session, tenant_with_chat_threads):
    """
    Regression for 7a9047f: connect prompt must not fire for source='chat' dashboard threads.
    """
    tenant_id, chat_thread_ids = tenant_with_chat_threads
    prompt = build_connector_prompt(client_id=tenant_id, db=db_session)
    # Prompt should be empty/None for tenants with only chat-source threads
    assert not prompt or "connect" not in prompt.lower(), (
        "Connect prompt fired for source='chat' thread — regression of 7a9047f"
    )
```

**Notes for nightly-commit-review implementation**:
- Import path: inspect `backend/services/connector_awareness.py` (45401ec) for correct module path
- Fixtures `two_tenants_with_connectors` and `tenant_with_chat_threads` — check existing conftest.py for patterns matching backend/tests/
- The isolation check may need to assert on connector slugs/names rather than client_ids if the prompt doesn't expose raw UUIDs — adjust based on prompt structure

### Mandate Check Results (run 93)

1. **GH #415 (Keys Koffee)**: 0 human responses after Day-21 mandate (run 92). Day 22 today. Still 0 business_hours rows.
2. **First real booking**: 0. AdminFunnelPage shows 0/3 tenants. Day 22.
3. **GH #413 (referral)**: 0 human responses after 4 autonomous runs (89-92). REFERRAL_REWARD_ENABLED not set.
4. **GH #399**: OPEN Day 10. 40 ai-ready issues stalled. Loop dead.
5. **GH #403**: OPEN Day 10. KB autopopulate stalled 69 days.
6. **GH #414**: CLOSED as duplicate of #415 ✓ (run 93 action complete)

### Confidence: HIGH

Direct evidence (3-day-old bug), pattern precedent (run 53), zero production risk, AUTONOMOUS-EXECUTABLE.

### Expected Impact

If nightly-commit-review implements this test:
- Cross-tenant data leakage in connector prompts is caught before it reaches production
- `7a9047f` regression is blocked permanently (the `source='chat'` filter case)
- Adds to the isolation test suite pattern established by run 53

---

## Bonus A: Parking Lot Update

**Referral email (Idea 1)** moves to parking lot with HIGH priority. Evidence: if GH #413 still has 0 human action by run 95 (2 runs from now), switch winner to "build item 10 (referral email) — code approach after comment approach exhausted."

**Voice G3 confirmation SMS (Idea 3)** moves to parking lot LOW priority — no voice bookings in production yet. Revisit after first voice booking confirmed.

---

## Run 94 Mandate

1. Did nightly-commit-review implement `test_connector_awareness_isolation.py`? Check git log for the test file.
2. GH #415 (Keys Koffee): human acted? First real booking?
3. GH #413: REFERRAL_REWARD_ENABLED set? If still no after run 94 check → run 95 switches winner to Idea 1 (build referral email — code beats comments).
4. GH #399 resolved? GH #403 resolved?
5. If test not implemented by nightly: evaluate if subconscious should implement directly vs escalate.
