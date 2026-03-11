Run a pre-deploy check before pushing to production.

1. No secrets exposed — scan staged/modified files for API keys, tokens, passwords, connection strings. Check .env is in .gitignore.
2. Backend imports cleanly — verify backend/main.py imports without errors.
3. Frontend builds — run `cd frontend && npm run build` and report errors.
4. Migration safety — new migrations are additive (no DROP without backup plan), sequential numbering is correct, no duplicates.
5. Schema consistency — modified Pydantic models match database schema. Leads use `client_id` and `status`.
6. CORS check — verify all deployment URLs are in the allowlist in backend/main.py.
7. No dangerous imports — no `from __future__ import annotations` in backend/routers/ files.
8. Widget sync — verify widget/ and frontend/public/widget/ files are identical.

Print a PASS/FAIL checklist. If anything fails, explain what to fix.
