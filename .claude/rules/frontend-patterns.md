---
paths:
  - "frontend/**/*.jsx"
  - "frontend/**/*.js"
  - "frontend/**/*.css"
---

# Frontend Patterns

- Dashboard uses a dark theme — match it for any new components
- Plan/subscription data must come from live API calls, never stale JWT claims. **Why:** JWT claims aren't refreshed when plan changes — caused stale upgrade prompts.
- Empty states should be helpful with CTAs, not just "0" or "No data"
- ALWAYS reference `design.md` in the project root before making any frontend visual changes — it defines colors, typography, spacing, components, and layout rules
- NEVER use localStorage in React artifacts

## Anti-AI-slop blocklist
Source: Anthropic's own frontend-design skill system prompt (leaked 2026-04). Defaults Claude reaches for in UI work look AI-generated. Ban them unless a design token/spec explicitly asks.

**Banned by default:**
- Gradient backgrounds (flat dark theme only — match existing dashboard)
- Emoji in UI chrome (labels, buttons, headers, empty states). Exception: user-generated content, or explicit brand token.
- SVG illustrations auto-generated as decoration (no inline "happy cloud" placeholders)
- Left-border-accent rounded cards ("colored stripe + rounded-lg" template)
- Fonts: `Inter`, `Roboto`, `Arial` as primary — use existing dashboard font stack from `design.md`
- Glassmorphism / frosted-glass backdrop blur on cards
- Over-rounded corners (`rounded-2xl` on everything) — match existing radius scale

**When to break:** widget surface spec overrides (tenant-branded), explicit user request, `design.md` token change. State the override in the commit.

**Rationale:** "one thousand no's for every yes" — distinctive UI requires actively steering away from LLM defaults, not just picking them.
