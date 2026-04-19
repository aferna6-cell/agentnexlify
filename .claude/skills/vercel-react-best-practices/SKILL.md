---
name: vercel-react-best-practices
description: React performance + bundle best practices from Vercel Engineering. Load when writing, reviewing, or refactoring components in frontend/src/, data fetching in frontend/src/utils/api/, or diagnosing slow re-renders or large bundles. Project uses Vite (not Next.js) — ignore Next-specific rules.
origin: https://github.com/vercel-labs/agent-skills
version: 1.0.0
triggers:
  - slow re-render
  - large bundle
  - react performance
  - waterfall fetch
  - memo component
  - bundle size
paths: frontend/src/**.jsx,frontend/src/**.tsx,frontend/src/utils/api/**
user-invocable: false
---

# Vercel React Best Practices

## When to Use
- Writing/refactoring components in `frontend/src/`
- Touching data fetching in `frontend/src/utils/api/`
- Diagnosing slow re-renders or large bundles
- Reviewing a PR that touches perf-sensitive UI

## When NOT to Use
- Next.js-specific rules (we're on Vite — skip)
- Backend-only changes
- Widget (different build pipeline — see `widget-rules.md`)

## 70 rules prioritized

Core categories relevant to our Vite/React 18 stack (upstream vercel-labs/agent-skills):

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
