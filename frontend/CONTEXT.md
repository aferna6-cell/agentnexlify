# Frontend Workspace
<!-- Last updated: 2026-03-31 -->

React/Vite dashboard for the AgentNexLiFy platform. Lives in `frontend/`.

## Stack

- Framework: React + Vite on Vercel (agentnexlify.com)
- Styling: Tailwind-style CSS, dark theme throughout
- Charts: Recharts
- Patterns: PascalCase components, functional components with hooks, responsive design

## Structure

- `frontend/src/pages/` — One file per dashboard page
- `frontend/src/components/` — Shared UI components (Sidebar, etc.)
- `frontend/src/utils/api/` — API client modules (one per feature area)
- `frontend/src/utils/api.js` — Core API utility
- `frontend/public/widget/` — Widget JS (must be identical to `/widget/agentnexlify-widget.js`)

## Critical Rules

- Dashboard uses a **dark theme** — match it for all new components
- Plan/subscription data must come from **live API calls**, never stale JWT claims
- Empty states should be helpful with CTAs, not just "0" or "No data"
- NEVER use localStorage in React artifacts
- Business logic goes through the API — not in frontend components
- Widget JS must be identical in `widget/` AND `frontend/public/widget/`
- agentnexlify.com is blocked by eduroam campus WiFi — network issue, not a bug

## Workflow: New Dashboard Page

1. Create page in `frontend/src/pages/PageName.jsx`
2. Add route in `frontend/src/App.jsx` (or router config)
3. Add sidebar link in `frontend/src/components/Sidebar.jsx`
4. Dark theme, live API data, helpful empty states

## Testing

- Frontend tests: `feature-name.test.tsx`
- Run frontend build (`npm run build`) before committing
- All 5 widget smoke test prompts must pass after API changes

## What to Avoid

- Breaking the landing page — it's live and the first thing prospects see
- Stale/hardcoded data — always fetch from the API
- Adding features to the UI without a corresponding API endpoint
- Non-dark-theme components that clash with the dashboard

## Known Issues

- Privacy Policy / ToS pages link to "#" (placeholder)
- Schema.org has placeholder social links
- Teaser bubble config field missing from widget config page
