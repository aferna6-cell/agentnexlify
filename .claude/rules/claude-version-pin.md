# Claude Code Version Pin — v2.1.98

## Rule
Use `claude-code@2.1.98` until Anthropic confirms the `cache_creation_input_tokens` inflation in v2.1.100+ is fixed.

## Why
Community proxy test (SolarXpander, r/ClaudeAI 2026-04): v2.1.100 sends fewer request bytes but gets billed ~20k MORE tokens than v2.1.98. Server-side inflation — not visible via `/context`.

| Version | Request size | Billed tokens (cache_creation) |
|---------|--------------|--------------------------------|
| v2.1.98 | 169,514 B | 49,726 |
| v2.1.100 | 168,536 B | 69,922 |
| v2.1.101 | 171,903 B | ~72,000 |

These aren't just "billing tokens" — `cache_creation_input_tokens` enter Claude's active context window:
- CLAUDE.md instructions diluted by 20k phantom tokens
- Quality degrades faster in long sessions
- Max limits burn ~40% faster than expected
- When Claude ignores rules, harder to diagnose

## How to apply
```bash
npx claude-code@2.1.98
```

Launch shell alias (optional):
```bash
alias claude='npx claude-code@2.1.98'
```

## When to unpin
Unpin when ANY of these true:
1. Anthropic changelog explicitly notes fix for cache_creation inflation
2. Independent proxy retest shows parity (<5% delta vs 2.1.98)
3. `/context` exposes the extra 20k so it's at least visible
4. Feature in 2.1.100+ becomes load-bearing for this project

## Caveats
- Community data only — not Anthropic-confirmed
- Single-tester methodology (HTTP proxy, --print mode, cold cache)
- Cache invalidation between accounts created confounding initial signal (per same post)
- Could be version/User-Agent routing artifact, not true inflation
- Treat as precautionary, not proven

## Sunset criteria
Review this rule monthly. Delete when any unpin condition met. Last review: 2026-04-15.

## Pointers
- Original post: r/ClaudeAI "Why Claude Code Max burns limits 40% faster with 20K less usable context"
- `claude-code-logger` proxy: https://github.com/solarxpander/claude-code-logger (community tool)
