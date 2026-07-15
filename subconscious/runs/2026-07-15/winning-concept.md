# Winning Concept — 2026-07-15 (Run 94)

## Recommendation

Replace `_SESSION_TURN_COUNTS: dict[str, int]` in `backend/services/widget_guard.py:141` with a bounded OrderedDict (maxsize=10,000, LRU eviction) to prevent unbounded memory growth in long-running Railway workers.

## Why This, Why Now

The nightly review on 2026-07-15 named the exact file and line number, making this zero-guesswork evidence. PR #431 shipped `widget_guard.py` yesterday — the code is fresh and the fix requires no context recovery. The unbounded dict is not an immediate crash risk, but Railway workers run continuously; a high-traffic tenant generating 10k+ session IDs over weeks of uptime will silently inflate worker memory with no natural eviction. Fixing it while the PR is 1 day old costs 5 minutes; fixing it after a production memory incident costs 2–3 hours plus postmortem. The fix is 8–10 lines, no new dependencies, and autonomous-executable via the nightly code-change channel.

## Implementation Sketch

**File:** `backend/services/widget_guard.py`

1. Find `_SESSION_TURN_COUNTS: dict[str, int] = {}` (line 141)
2. Add import at top of file: `from collections import OrderedDict`
3. Replace the bare dict with a bounded LRU structure:
   ```python
   class _BoundedDict:
       """dict[str, int] capped at maxsize entries; evicts oldest on overflow."""
       def __init__(self, maxsize: int = 10_000):
           self._data: OrderedDict[str, int] = OrderedDict()
           self._maxsize = maxsize
       def get(self, key: str, default: int = 0) -> int:
           return self._data.get(key, default)
       def __setitem__(self, key: str, value: int) -> None:
           self._data[key] = value
           self._data.move_to_end(key)
           if len(self._data) > self._maxsize:
               self._data.popitem(last=False)
       def __getitem__(self, key: str) -> int:
           return self._data[key]

   _SESSION_TURN_COUNTS = _BoundedDict(maxsize=10_000)
   ```
4. Verify `check_turn_budget()` and `screen_widget_input()` still call `.get()` and `[]` — both work unchanged with the new class.
5. Add regression test in `backend/tests/test_widget_guard.py`: fill 10,001 sessions, assert dict stays at 10,000 (oldest evicted).
6. Commit: `fix(widget_guard): cap _SESSION_TURN_COUNTS at 10k entries (LRU eviction)`

**No new dependencies. No migration. No config change.**

## What This Replaces

Previous active direction: "GH #413 referral checklist 10/10 complete — REFERRAL_REWARD_ENABLED=1 is sole remaining step" (run 93 winner, status: pending_human_action). That item requires Railway env var change — human-only, no autonomous path. Run 94 winner is fully autonomous.

## Mandate Check Results (Run 94)

| Item | Status |
|------|--------|
| GH #413 human response / REFERRAL_REWARD_ENABLED=1 | ❌ NOT SET — 0 human responses after 4 autonomous comments |
| First referral-converted lead | ❌ Program not activated |
| Keys Koffee GH #415 actioned | ❌ 0 human responses — Day 23 |
| GH #399 resolved | ❌ OPEN Day 12+ — 40 ai-ready issues blocked |
| GH #403 resolved | ❌ OPEN Day 12+ — KB 72+ days stale |
| Widget guard wiring confirmed | ✅ CONFIRMED — widget_chat.py lines 34 + 684 |

## Confidence: HIGH

Evidence is direct (nightly named exact file:line). Fix is bounded and testable. No ambiguity about what to do or where.

## Run 95 Mandate

1. Was widget_guard fix committed by nightly review? Check nightly-2026-07-16 log.
2. Does regression test pass? (`backend/tests/test_widget_guard.py` — new LRU eviction test)
3. GH #413: REFERRAL_REWARD_ENABLED=1 set? First referral lead visible? (Day 24+)
4. Keys Koffee GH #415: actioned? First booking? (Day 24+)
5. GH #399 + #403: resolved? (Day 13+)
6. Parking lot candidates: Step 9F (nightly infra staleness check), attribution dashboard GH issue, BotHealthPage.jsx.
