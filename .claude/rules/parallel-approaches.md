---
paths:
  - "**/*"
---

# Parallel Approaches — 2 Agents, Best Wins

## When to use
- Approach genuinely unclear (2+ viable architectures)
- Risky task where fallback is worth compute cost
- User says "try a few ways" or "what's the best approach"
- Refactor with unknown blast radius
- Algorithm selection where tradeoffs aren't obvious

## How
Spawn 2 agents in parallel using `isolation: "worktree"`. Each gets different strategy. Compare on:
1. Tests pass
2. Simpler code
3. Performance
4. Reviewer approval

Take winner. Discard losing worktree.

## Don't use for
- Straightforward tasks with one obvious solution
- Tasks under 5 minutes (overhead > benefit)
- Tasks where both approaches touch shared state (use sequential instead)
- Simple lookups or formatting

## Pattern
```
Agent({isolation: "worktree", prompt: "Approach A: iterate over array..."})
Agent({isolation: "worktree", prompt: "Approach B: recursive divide-and-conquer..."})
```
Send in single message for true parallelism.

## Explicit fan-out phrasing (Opus 4.7)
4.7 spawns fewer subagents by default. Parallel execution needs the directive spelled out literally, or the model runs sequentially. Cross-ref: `opus-4-7-prompting.md §4`.

**Phrasings that work (use these):**
- "Spawn subagents in the same turn to investigate X, Y, Z."
- "Fan out to 3 worktrees in parallel, each with strategy A/B/C."
- "Dispatch agent1 + agent2 + agent3 concurrently."
- "Run N Agent calls in a single tool-call batch — do not serialize."
- "Parallel worktree agents: A explores approach X, B explores approach Y. Same turn."

**Anti-phrasings (4.7 under-delegates):**
- "Investigate X, Y, Z." — done sequentially
- "Consider multiple angles." — picks one, skips the rest

## Evaluate
Read both worktree outputs. Run tests in each. Pick winner. Document why in commit/plan.
