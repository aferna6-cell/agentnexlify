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
