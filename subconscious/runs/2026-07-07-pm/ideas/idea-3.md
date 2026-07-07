# Idea 3: Activate Issue-to-PR Loop for Zapier Plan_Status Bug (#107)

**Evidence:** `docs/dev-knowledge/bug-patterns.md` entry dated 2026-04-30: "Zapier API key client lookup did not enforce plan_status" — cancelled/past-due tenants with un-revoked API keys still authenticate. Fix specified: "add `plan_status IN ('active','trialing')` check inside `_get_api_key_client`, return 402/403 for cancelled tenants." GH #107 filed; no code fix in 68 days. Bug-patterns.md calls it "TODO — backend-dev to add..." which is exactly the issue-to-pr-loop scope. Moratorium check: governance.json shows pending_approvals=1 (run 81's #385 label-add, pending tonight's nightly). max_pending_approvals=2. Adding a second ai-ready item would bring pending to 2 — at the limit but not over.

**Action:** Recommend adding `ai-ready` label to GH #107 so issue-to-pr-loop implements the single-file fix. The fix is Low risk (one function in `backend/services/zapier_auth.py`, regression test already specified in bug-patterns.md). Label should be added AFTER #385 label is confirmed applied (tonight's nightly).

**Impact:** Closes 68-day-old security/revenue gap. Cancelled tenants currently have unrevoked API access. Fix is 1-function, 10-line change + regression test — squarely in autonomous execution scope.

**Category:** code_health

**Confidence pre-debate:** MEDIUM — valid, but pending_approvals would hit max (2). Timing dependency on #385 nightly execution. Not as high-leverage as KB cron fix.
