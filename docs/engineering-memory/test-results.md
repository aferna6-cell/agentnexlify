# Test Results
_Track what features have been tested, what passed, what failed._

## 2026-03-24

| Test | Result | Notes |
|------|--------|-------|
| Backend import check | PASS | `from backend.main import app` succeeds |
| Frontend build | PASS | `npm run build` completes in ~4s, no errors |
| No `from __future__ import annotations` in routers | PASS | grep found 0 matches |
| No `except BaseException` in backend | PASS | grep found 0 matches |
| No `tenant_id` on conversations table queries | PASS | All use `client_id` correctly |
| No `tenant_id` on leads table queries | PASS | All use `client_id` correctly |
| Widget files in sync | PASS | `diff` returns no differences |
| No bare `except:` blocks | PASS | All except blocks have specific exceptions |
| Plan name fallbacks in frontend | PASS | foundation/operations mapped to growth/professional |
| lead_stage references | OK | Only used as event name strings, not column queries |
