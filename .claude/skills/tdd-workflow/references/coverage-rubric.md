# TDD Workflow — Coverage Rubric & Test Patterns Reference

## Coverage Thresholds

```json
{
  "jest": {
    "coverageThresholds": {
      "global": {
        "branches": 80,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    }
  }
}
```

Note: backend currently sits at ~45%. Don't block PRs on coverage alone — block on PASS/FAIL of existing tests.

## Unit Test Pattern (Jest/Vitest)

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from './Button'

describe('Button Component', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Click</Button>)
    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })
})
```

## API Integration Test Pattern

```typescript
describe('GET /api/markets', () => {
  it('returns markets successfully', async () => {
    const request = new NextRequest('http://localhost/api/markets')
    const response = await GET(request)
    const data = await response.json()
    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(Array.isArray(data.data)).toBe(true)
  })

  it('validates query parameters', async () => {
    const request = new NextRequest('http://localhost/api/markets?limit=invalid')
    const response = await GET(request)
    expect(response.status).toBe(400)
  })
})
```

## E2E Test Pattern (Playwright)

```typescript
import { test, expect } from '@playwright/test'

test('user can search and filter markets', async ({ page }) => {
  await page.goto('/')
  await page.click('a[href="/markets"]')
  await expect(page.locator('h1')).toContainText('Markets')
  await page.fill('input[placeholder="Search markets"]', 'election')
  await page.waitForTimeout(600)
  const results = page.locator('[data-testid="market-card"]')
  await expect(results).toHaveCount(5, { timeout: 5000 })
})
```

## Mocking External Services

### Supabase Mock
```typescript
jest.mock('@/lib/supabase', () => ({
  supabase: {
    from: jest.fn(() => ({
      select: jest.fn(() => ({
        eq: jest.fn(() => Promise.resolve({
          data: [{ id: 1, name: 'Test Market' }],
          error: null
        }))
      }))
    }))
  }
}))
```

### Redis Mock
```typescript
jest.mock('@/lib/redis', () => ({
  searchMarketsByVector: jest.fn(() => Promise.resolve([
    { slug: 'test-market', similarity_score: 0.95 }
  ])),
  checkRedisHealth: jest.fn(() => Promise.resolve({ connected: true }))
}))
```

## Test File Organization

```
src/
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   └── Button.test.tsx       # Unit tests
├── app/
│   └── api/
│       └── markets/
│           ├── route.ts
│           └── route.test.ts     # Integration tests
└── e2e/
    ├── markets.spec.ts           # E2E tests
    └── auth.spec.ts
```

## Anti-Patterns

WRONG: Testing implementation details
```typescript
expect(component.state.count).toBe(5)
```

CORRECT: Test user-visible behavior
```typescript
expect(screen.getByText('Count: 5')).toBeInTheDocument()
```

WRONG: Brittle selectors
```typescript
await page.click('.css-class-xyz')
```

CORRECT: Semantic selectors
```typescript
await page.click('button:has-text("Submit")')
await page.click('[data-testid="submit-button"]')
```

WRONG: No test isolation
```typescript
test('creates user', () => { /* ... */ })
test('updates same user', () => { /* depends on previous test */ })
```

CORRECT: Independent tests — each test sets up its own data.

## CI/CD Integration

```yaml
- name: Run Tests
  run: npm test -- --coverage
- name: Upload Coverage
  uses: codecov/codecov-action@v3
```

## Flaky Test Strategies

```bash
npx playwright test tests/search.spec.ts --repeat-each=10
npx playwright test tests/search.spec.ts --retries=3
```

Race condition fix: use `page.locator('[data-testid="button"]').click()` (auto-waits) not `page.click('[data-testid="button"]')`.

Network timing fix: `await page.waitForResponse(resp => resp.url().includes('/api/data'))` not `await page.waitForTimeout(5000)`.
