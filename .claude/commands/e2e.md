---
description: Generate and run Playwright E2E tests for AgentNexLiFy. Uses Playwright MCP for browser automation.
---

# E2E Testing

Generate or run Playwright E2E tests for: `$ARGUMENTS`

## Process

1. Identify the user flow to test
2. Check if a test already exists in `tests/` or `e2e/`
3. Generate Playwright test using Page Object Model pattern
4. Run via Playwright MCP (`mcp__playwright__*`) or `npx playwright test`
5. Capture screenshots on failure
6. Report results with failure details and flake risk

## AgentNexLiFy-Specific Flows

Priority test targets:
- **Widget chat**: Load widget → send message → receive AI response → lead captured
- **Auth**: Signup → login → dashboard → logout
- **Onboarding**: Signup → wizard step 1-6 → embed code
- **Lead management**: Create lead → update status → view in CRM
- **Appointments**: Book → confirm → complete → trigger automation
- **Billing**: Select plan → Stripe checkout → plan active

## Rules

- Base URL: `http://localhost:5173` (frontend dev) or `https://agentnexlify.vercel.app` (prod)
- API: `http://localhost:8000` (dev) or `https://agentnexlify-production.up.railway.app` (prod)
- Use `data-testid` attributes for selectors when available
- Always wait for network idle before assertions
- Test tenant isolation — never leak data between tenants
