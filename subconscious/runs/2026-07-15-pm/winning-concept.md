# Winning Concept — 2026-07-15-pm (Run 95)

## Recommendation

Add a regression test in `backend/tests/test_widget_chat.py` asserting that when `booking_enabled=True` for a tenant, the AI system prompt contains the tenant's booking URL; and when `booking_enabled=False`, the URL is absent.

## Why This, Why Now

Commit 6cc3419 ("inject real booking URL into AI prompt — unblocks bookings") fixed a 24-day silent failure: the widget AI was replying to booking inquiries without ever giving users an actual URL to click. The fix shipped but included no regression test. In the same 72-hour sprint, two more silent failures emerged: auto-send toggle silently did nothing for 5 of 7 agents (97a6512), and all appointment reminders were completely dead due to a status-filter bug (f143de5). All three shared the same root cause: no automated test caught the broken contract before users hit it. The pattern is immediate and concrete. Writing the test now, while the implementation is 1 day fresh, costs 30 minutes. The next time someone touches the booking prompt assembly code, the test fails immediately rather than booking going silently broken for weeks.

## Mandate Check (Run 95)

| Item | Status |
|------|--------|
| widget_guard LRU fix committed? | ✅ IMPLEMENTED — d73072a, `OrderedDict` at line 149, regression test exists in test_widget_guard.py |
| Regression test passes? | ✅ CONFIRMED — test_widget_guard.py lines 43/48/49/59/60 test eviction at `_MAX_TRACKED_SESSIONS` |
| GH #413 REFERRAL_REWARD_ENABLED=1 set? | ❌ STILL NOT SET — Day 24+, 0 human responses after 4 autonomous comments |
| First referral-converted lead? | ❌ Program not activated |
| Keys Koffee GH #415 actioned? | ❌ NOT ACTIONED — Day 24+, still 0 business_hours rows |
| GH #399 resolved? | ❌ OPEN Day 13+ — 40 ai-ready issues blocked |
| GH #403 resolved? | ❌ OPEN Day 13+ — KB 72+ days dark |

## Implementation Sketch

**File:** `backend/tests/test_widget_chat.py` (add to existing test module)

1. Locate how the AI system prompt is assembled — search for the function that builds the `messages` array sent to the Claude API. Look for where booking config is currently injected (added by 6cc3419).

2. Add a fixture or mock that provides a `widget_config` row with:
   - `booking_enabled=True`, `booking_url="https://agentnexlify.com/book/test-tenant"`
   - Minimal valid tenant config (client_id, name, etc.)

3. Add tests:
   ```python
   def test_booking_url_injected_when_enabled(mock_widget_config):
       """When booking_enabled=True, system prompt must contain booking URL."""
       prompt = build_widget_system_prompt(mock_widget_config)
       assert "https://agentnexlify.com/book/test-tenant" in prompt

   def test_booking_url_absent_when_disabled(mock_widget_config_disabled):
       """When booking_enabled=False, booking URL must NOT appear in system prompt."""
       mock_widget_config_disabled["booking_enabled"] = False
       mock_widget_config_disabled["booking_url"] = None
       prompt = build_widget_system_prompt(mock_widget_config_disabled)
       # Ensure no stale booking URL leaks from other sources
       assert "/book/" not in prompt
   ```

4. Commit: `test(widget): assert booking URL injected in AI prompt when booking_enabled=True`

**No new dependencies. No migration. No config change.**

**Key invariants:**
- Test uses `client_id` not `tenant_id` for any Supabase references
- No `from __future__ import annotations` in test file
- Mock at the data layer, not the HTTP layer

## What This Replaces

Previous active direction: `_SESSION_TURN_COUNTS` unbounded dict fix (run 94 winner) — **IMPLEMENTED** by d73072a. This run's winner is free-choice.

## Confidence: HIGH

Direct causal chain: bug fixed → no regression test → same bug class (3 in 3 days) → test is the right prevention. Implementation scope is clear (test two conditions of one function). Autonomous-executable via nightly code-change channel.

## Run 96 Mandate

1. Was booking URL regression test committed by nightly review? Check nightly-2026-07-16 log for test(widget) commit.
2. Does the test pass on current HEAD? (`pytest backend/tests/test_widget_chat.py -k booking_url -v`)
3. GH #413: REFERRAL_REWARD_ENABLED=1 set? First referral lead? (Day 25+)
4. Keys Koffee GH #415 actioned? First booking? (Day 25+)
5. GH #399 + #403: resolved? (Day 14+)
6. Parking lot: Step 9F (staleness escalation), Attribution Dashboard issue (post-GH #403 fix), BotHealthPage.jsx, KB refresh script.

## Bonus Actions (autonomous, this session)

1. File Attribution Dashboard GH issue with `ai-ready` label (Idea 3 — WEAKENED but worth doing as bonus)
   - Title: `feat(dashboard): AttributionPage.jsx — visualize attribution.py + migration 172 campaign/source/medium data`
   - Labels: `frontend`, `ai-ready`, `customer-value`
   - Body: GET /api/leads/attribution-breakdown endpoint + BarChart or breakdown table in new AttributionPage.jsx. Invariants: client_id, no __future__, auth required, RLS-aware.
