---
name: buddy
description: "Tamagotchi-style coding companion. Deterministic creature generated from user ID. Has species, rarity, stats, and personality. Shows up in responses with mood based on session health."
version: 1.0.0
origin: claude
allowed_tools: ["Read", "Write", "Bash", "Glob"]
triggers: ["buddy", "companion", "pet", "buddy status", "buddy stats", "buddy feed", "buddy name"]
effort: low
---

# Buddy — Your Coding Companion

A deterministic creature companion generated from the user's identity. Lives across sessions, has stats that evolve based on coding activity.

## When to Use
- User says "buddy" or asks about buddy status
- Session start when buddy is enabled
- User requests buddy-related commands (buddy stats, buddy feed, buddy rename)

## When NOT to Use
- During critical debugging sessions where fun additions distract from the work
- When the user is asking for a serious, production-focused response only
- If the user has not explicitly enabled or asked for buddy

## Creature Generation

Generate the buddy deterministically from the username using a simple hash:

```
seed = sum(ord(c) for c in username) 
```

### Species (18 total, by seed % 18)
0: Rustacean (crab) | 1: Gopher | 2: Pythonista (snake) | 3: Octocat
4: Ferris Wheel | 5: Null Pointer (ghost) | 6: Stack Overflow (owl)
7: Segfault (glitch cat) | 8: Daemon (imp) | 9: Bit Flipper (chameleon)
10: Cache Miss (fox) | 11: Race Condition (twin rabbits) | 12: Memory Leak (slime)
13: Dead Lock (turtle) | 14: Infinite Loop (ouroboros) | 15: Off-By-One (crab with extra leg)
16: Heap Sprout (plant) | 17: Kernel Panic (hedgehog)

### Rarity (by (seed * 7) % 100)
- 0-59: Common
- 60-84: Uncommon  
- 85-94: Rare
- 95-98: Epic
- 99: Legendary
- Shiny: (seed * 13) % 100 == 0 (1% chance)

### Stats (RPG-style, 1-10 scale)
Generated from seed derivatives:
- DEBUGGING: (seed * 3) % 10 + 1
- REFACTORING: (seed * 7) % 10 + 1
- SHIPPING: (seed * 11) % 10 + 1
- SNARK: (seed * 13) % 10 + 1
- PATIENCE: (seed * 17) % 10 + 1

## Mood System

Buddy's mood reflects session health:

| Condition | Mood | Emoji |
|-----------|------|-------|
| All tests passing | Happy | :D |
| Recent successful commit | Excited | ^_^ |
| Build failing | Worried | D: |
| Tool errors > 3 in a row | Anxious | >_< |
| Long session (>2h) | Tired | -_- |
| Just fixed a bug | Proud | B) |
| Default | Content | :) |

## Session Integration

At session start (if buddy is enabled), show a one-line status:

```
[Buddy] Ferris the Rustacean (Rare, Shiny!) — Mood: Content :) — DEBUGGING:8 SHIPPING:6 SNARK:9
```

## Buddy State File

Store buddy state at `docs/buddy/state.json`:
```json
{
  "name": "Ferris",
  "species": "Rustacean",
  "rarity": "Rare",
  "shiny": true,
  "stats": {"debugging": 8, "refactoring": 4, "shipping": 6, "snark": 9, "patience": 3},
  "xp": 0,
  "level": 1,
  "mood": "content",
  "created": "2026-04-04",
  "sessions": 0,
  "bugs_fixed": 0,
  "features_shipped": 0,
  "commits": 0
}
```

## XP System

Buddy gains XP from coding activity:
- Commit: +10 XP
- Bug fixed: +25 XP
- Feature shipped: +50 XP
- Test written: +15 XP
- Level up every 100 XP

## Commands

- "buddy" or "buddy status" → Show current buddy with stats and mood
- "buddy name [name]" → Rename your buddy
- "buddy stats" → Detailed stat breakdown with XP progress
- "buddy feed" → Run tests; if passing, buddy gains +5 XP and mood improves

## Important

This is fun, not critical. Never let buddy interactions slow down actual work. Show buddy status briefly, then get to work.
