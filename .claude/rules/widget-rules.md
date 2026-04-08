---
paths:
  - "widget/**/*"
  - "frontend/public/widget/**/*"
---

# Widget Rules

- Widget JS must be IDENTICAL in `widget/` AND `frontend/public/widget/`. **Why:** Widget is served from both paths depending on deployment. Mismatch = different behavior for different customers.
- Widget is tenant-scoped. Every request carries an API key that maps to a tenant.
- CORS is configured in main.py with `allow_origins=["*"]` and `allow_credentials=False` — this is intentional for cross-origin widget embedding. Don't restrict it.
- If widget stops working on external sites, check CORS config in `backend/main.py` first.
- Use `agent-browser` via Bash for testing widget behavior (real browser, JS execution).
