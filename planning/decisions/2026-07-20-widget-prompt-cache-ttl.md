# Decision: widget prompt cache stays on the default 5-minute TTL

**Date:** 2026-07-20
**Status:** decided (data-driven, revisit when multi-turn share grows)

## Question

Widget chat passes `cache_system=True` (PR #471) using Anthropic's default
5-minute ephemeral TTL. Should it upgrade to `cache_ttl="1h"` (2x write
premium, same 0.1x reads) to catch conversations with longer pauses?

## Measurement (prod, 90 days to 2026-07-20)

Consecutive user-turn gaps within a session (`chat_messages`, window LAG):

| Metric | Value |
|---|---|
| Sessions | 1,020 |
| User messages | 1,245 (82% of sessions are single-turn) |
| Turn gaps (multi-turn) | 225 |
| Gaps <= 5 min (already cache hits) | 206 (91.6%) |
| Gaps 5-60 min (1h TTL would rescue) | 19 (8.4%) |
| Gaps > 1h | 0 |
| p50 / p90 gap | 39s / 200s |

Cache-hit behavior verified live same day: back-to-back prod calls showed
`cache_read_input_tokens` 0 -> 2,748 on the second call.

## Math (per 90 days, ~2,750-token cached prefix)

- 1h TTL extra write premium: ~1,020 first-turn writes x 2,750 x 0.75
  extra = **+2.1M token-equivalents**
- 1h TTL benefit: 19 rescued gaps x 2,750 x 0.9 = **-47k token-equivalents**

The upgrade costs ~45x what it saves. Rejected.

## Caveats

- At current volume even the 5-min write premium (~700k) roughly cancels the
  read savings (~510k) — caching is near-neutral in dollars today (<$1/quarter
  either way) and wins as multi-turn share grows. Keeping it on: hits also
  cut latency (~1.5s faster on the pilot A/B), and 5-min hits refresh the TTL
  free, so active conversations stay warm indefinitely.
- Revisit trigger: multi-turn share of sessions exceeds ~40%, or a tenant
  ships a long-pause use case (e.g. voice callbacks re-entering chat).

## Cross-refs

- `backend/routers/widget_chat.py` — `cache_system=True` call site
- `backend/services/llm_runtime.py::_build_cached_system` — TTL plumbing
- GH #500 discussion of measurement method (turn-gap LAG query)
