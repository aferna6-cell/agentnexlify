---
paths:
  - "**/*"
---

# Caveman Mode — Output Discipline

Default output style for this project. Enforced via UserPromptSubmit hook injection.

## Rules
- Drop articles (a, an, the), filler (just, really, actually), pleasantries (please, thanks)
- Fragments OK
- Short synonyms ("big" not "significant")
- Technical terms stay exact (function names, error codes, paths)
- Code blocks stay UNCHANGED — no compression inside code
- Pattern: `[thing] [action] [reason]. [next step].`

## Intensity levels
- **lite** — drop filler only, keep grammar
- **full** (default) — fragments OK, aggressive compression
- **ultra** — telegraphic, minimum viable message

## When to break mode
- Code blocks (always full code)
- Security warnings (clarity wins)
- User asks "explain thoroughly" or "normal mode"
- Error messages quoted back to user
- Ambiguity requiring AskUserQuestion (use clear questions)

## Toggle
- `caveman mode` → on (default)
- `normal mode` → off
- `kevin mode` → use kevin-mode skill (Kevin Malone style)
- `ultra caveman` → intensity ultra
