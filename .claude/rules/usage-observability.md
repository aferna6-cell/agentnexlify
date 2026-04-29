# Usage Observability — Watch the Number

## Rule
Cache hit rate, token burn, and session window are invisible by default. Install one historical dashboard + one real-time monitor. If you can't see the number, you can't fix it.

## Tools

### Historical (Pro / Max / Team)
**phuryn/claude-usage** — long-term breakdown by session/day/week/all-time. Find where the spend went.

```bash
npx claude-usage
# or pin: npx claude-usage@latest
```

Source: https://github.com/phuryn/claude-usage

### Real-time (5-hour window + active session)
**Gronsten/claude-usage-monitor** — current 5-hour window + active session tokens with color thresholds. Know how close to cap right now.

```bash
npx claude-usage-monitor
```

Source: https://github.com/Gronsten/claude-usage-monitor

### API cache hit rate (API users only)
Anthropic dashboard: https://platform.claude.com/usage/cache

Not relevant for Pro/Max/Team subscriptions — those don't expose cache hit rate.

## When to use which
- End of week / before billing cycle → claude-usage (where did spend go)
- Mid-session, approaching limit → claude-usage-monitor (am I about to hit cap)
- API project work → platform.claude.com/usage/cache (cache hit rate <90% means prefix is being invalidated)

## Targets
- Cache hit rate (API): >=90% on 5-min TTL, >=97% on 1-hour
- Session token burn: stay under 250k for quality (per `one-task-one-chat.md` 25% threshold)
- Weekly cap on Max 20x: should not burn weekly quota in <3 days under normal workflow

## Triage when burn is high
1. Check `rtk gain` — what's RTK saving? If 0, hook not installed (`rtk init -g`)
2. Check session length — sprawled past 50% context? `/compact`
3. Check effort level — `xhigh` default on mechanical work? Drop to `medium` (`effort-per-prompt.md`)
4. Check subagent usage — bulk research/scan in parent context? Delegate (`model-routing.md`)
5. Check MCP load — disabled unused plugins? See `plugins.md` low-priority list

## Anti-patterns
- Never optimize burn without measuring first — install a dashboard
- Never assume cache hit rate is fine — it's invisible by default; check it
- Never trust `/context` alone — known to under-report cache_creation_input_tokens (`claude-version-pin.md`)

## Cross-refs
- `rules/one-task-one-chat.md` — context budget hygiene
- `rules/effort-per-prompt.md` — effort dial
- `rules/model-routing.md` — subagent delegation
- `rules/claude-version-pin.md` — `/context` reliability caveat
- `rules/plugins.md` — disable unused plugins
- Source: SolarXpander cost-optimization writeup (2026-04-26)
