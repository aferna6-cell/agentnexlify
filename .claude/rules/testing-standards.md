---
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "frontend/src/**/*.test.js"
---

# Testing Standards

- NEVER add new features without running the test suite first
- Test behavior, not implementation details
- Frontend tests: use Vitest (`cd frontend && npx vitest run`)
- Every bug fix should include a test that would have caught it
- Integration tests should use real Supabase queries where possible, not mocks. **Why:** Mock/prod divergence has masked broken migrations in the past.
- E2E tests use Playwright MCP for browser automation
