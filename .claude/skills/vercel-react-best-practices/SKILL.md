---
name: vercel-react-best-practices
description: React performance + bundle best practices from Vercel Engineering. Load when writing, reviewing, or refactoring components in frontend/src/, data fetching in frontend/src/utils/api/, or diagnosing slow re-renders or large bundles. Project uses Vite (not Next.js) — ignore Next-specific rules.
origin: https://github.com/vercel-labs/agent-skills
version: 1.0.0
---

# Vercel React Best Practices (thin wrapper)

70 rules from upstream, prioritized by impact. Core categories relevant to our Vite/React 18 stack:

1. **Eliminating waterfalls (CRITICAL, `async-` prefix)** — parallelize independent fetches with `Promise.all` or `Promise.allSettled`. Never chain awaits when data is independent.
2. **Bundle size (CRITICAL, `bundle-` prefix)** — dynamic `import()` for heavy routes; tree-shake; avoid barrel exports that pull the world.
3. **Client-side data fetching (MEDIUM-HIGH, `client-` prefix)** — use SWR/TanStack Query patterns; dedupe inflight requests.
4. **Rendering (MEDIUM, `render-` prefix)** — `React.memo` for expensive children, stable keys on lists, `useMemo` for derived state ≥10ms compute.
5. **Image optimization** — Vite's asset pipeline; lazy `loading="lazy"` on below-fold images.

## AgentNexLiFy-specific overrides
- **No localStorage** in React artifacts or claude.ai-embedded components (per `.claude/rules/frontend-patterns.md`).
- Auth JWT lives in `AuthContext`, headers set via `frontend/src/utils/api/client.js`.
- Plan data fetched live on mount to avoid stale upgrade prompts (don't cache in JWT claims).
- Ignore Next.js-specific rules (RSC, App Router, middleware) — we use Vite.

## Full upstream skill
https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/SKILL.md

Install upstream version:
```
npx skillsadd vercel-labs/agent-skills
```
