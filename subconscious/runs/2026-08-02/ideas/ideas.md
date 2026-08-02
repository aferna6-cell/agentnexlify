# Ideas — Run 101 (2026-08-02)

## Evidence Digest

1. **Step 9G ABSENT** — Run 100 winner not implemented. KB stale 10 days (last run 2026-07-23). Step 9F fires correctly (nightly-2026-07-22 confirmed "Step 9F: KB STALE (9 days)") but cannot self-repair — alert-only posture leaves the gap open indefinitely.
2. **PR #619 (b67710c, 2026-08-02)** — Largest commit in project history: 62 files, 13,916 insertions. Five new capability phases: inbox monitoring, SMS agent, social publish+images, prospecting, in-chat connectors. All critical invariants passed nightly review, but enormous new surface area with new external integrations (Gmail, social APIs, Twilio).
3. **GH #536 HIGH open 10 days** — INTEGRATIONS_ENC_KEY not in Railway, blocks migration 176 (Gmail OAuth credential encryption). PR #619 depends on this path being available.
4. **connector_awareness `client_id` bug (fixed 2026-08-02, a98ea21)** — `connector_registry.py` queried `tenant_api_keys` with `.eq("tenant_id", client_id)` instead of `.eq("client_id", client_id)`. Every Zapier connector-status check silently reported "not connected" for all tenants. Same class as CLAUDE.md Critical Invariant #1 on a different table. Auto-fixed by nightly.
5. **GH #399 still open** — AUTOPILOT_GH_TOKEN expired, autopilot-issue-loop stalled, 3 ai-ready issues queued.

---

### Idea 1: Step 9G Carry-Forward — KB Autopopulate Self-Heal Trigger
**Evidence:** Run 100 winner. KB stale 10 days. Step 9F fires correctly but only alerts. GH #403 has received multiple Step 9F comments; zero human action in months. Previous SKILL.md-edit channel delivered Steps 9B–9F each in 1 cycle. Run 101 mandate condition #1 fires.
**Action:** Add Step 9G bash block after Step 9F in `.claude/skills/nightly-commit-review/SKILL.md`. Block: if `DAYS_STALE -gt 7`, run `gh workflow run kb-autopopulate.yml`, wait 30s, check conclusion. If success: log it. If failure: comment on GH #403 with specific secret names needed. Total: ~30 bash lines.
**Impact:** KB staleness repairs automatically within 1 nightly cycle instead of alerting indefinitely. Prevents future 63-day silent gaps. Chat AI quality restored within hours of stale condition.
**Category:** operational

---

### Idea 2: GH #536 INTEGRATIONS_ENC_KEY Escalation — Comment Linking PR #619 Gmail Dependency
**Evidence:** GH #536 HIGH open since 2026-07-23 (10 days). nightly-2026-08-01 lists it as blocked on "human credentials/infra provisioning". PR #619 ships Gmail connector (518 lines: `gmail_connector.py`, `gmail_integration.py`) that depends on `INTEGRATIONS_ENC_KEY` for OAuth token storage. Without this env var, any tenant attempting Gmail OAuth get a 500 on the callback route.
**Action:** Comment on GH #536 via `mcp__github__add_issue_comment` with: "PR #619 (Gmail connector, 62 files, 2026-08-02) is now deployed and depends on `INTEGRATIONS_ENC_KEY` for `oauth_tokens` encryption (migration 176). Railway > Variables > INTEGRATIONS_ENC_KEY = `python -c \"import secrets; print(secrets.token_hex(32))\"`. Then apply migration 176 in Supabase dashboard."
**Impact:** Unblocks Gmail connector feature for any tenant who tries to use it. Without it, OAuth callbacks 500.
**Category:** operational

---

### Idea 3: Silent Tenant Monitoring — Add Step 9H Paying-Tenant Conversation Heartbeat
**Evidence:** bug-patterns.md (2026-07-23): "Keys Koffee's site redeploy dropped the widget embed ~2026-06-14. Conversations flatlined to zero for a paying tenant and no system flagged it; discovered only by a manual funnel audit." Prevention note: "every automation and tenant integration needs a heartbeat that distinguishes 'ran and found nothing' from 'never ran': scheduled jobs always write a run log; tenant-level outcome metrics (conversations/7d) alert on zero for paying tenants." No heartbeat exists.
**Action:** File GH issue titled "feat(nightly): Step 9H — paying tenant conversation heartbeat (0 conversations in 7d = alert)" with ai-ready label. Implementation: Step 9H queries `conversations` table via Supabase (or `healthz` endpoint cross-referencing tenant list) and fires if any paying tenant has 0 conversations in 7 days.
**Impact:** Catches silent tenant failures in <24h instead of 5+ weeks. Revenue protection: a tenant paying $99/mo with a broken widget is a churn risk.
**Category:** operational

---

### Idea 4: capabilities PR #619 Integration-Level Test Gap Audit
**Evidence:** PR #619 (b67710c) introduces 5 new external integration surfaces — Gmail OAuth, social media posting (Facebook/Instagram GBP), prospecting (web scrape + AI classify), inbox triage (AI classify + auto-respond), SMS agent. Nightly confirmed PASS on invariants but only checked critical-invariant compliance, not integration failure modes. `test_connector_registry.py` has 623 insertions and `test_escalations.py` has 1084 insertions (good) but `test_gmail_connector.py` (694 lines) covers Gmail integration at unit level only — no OAuth callback error path test visible.
**Action:** Run `python -m pytest backend/tests/test_gmail_connector.py -v` and `backend/tests/test_inbox_triage.py -v` to find any failing tests in new services; file ai-ready GH issue with specific gap.
**Impact:** Prevents silent 500s in new email/social/prospecting paths before any tenant hits them.
**Category:** code_health

---

### Idea 5: AUTOPILOT_GH_TOKEN Rotation Escalation — Comment Update on GH #399
**Evidence:** GH #399 open since 2026-07-04 (29 days). All nightly runs post-2026-07-22 note it as pre-existing but make no new comments. The issue is a single Railway secret rotation (AUTOPILOT_GH_TOKEN), 2-minute action. 3 ai-ready issues currently queued (GH #69, #70, #114). The issue has received no human action in 29 days.
**Action:** Post fresh Day-29 escalation comment on GH #399 with: (1) issue cost = 29 days × 3 ai-ready issues = ~87 engineering-hours of queued automation blocked; (2) GH token rotation steps; (3) explicit link to ai-ready queue.
**Impact:** If human rotates token, ai-ready issues start processing again. Potential same-day PR on GH #114 (which already has a draft PR linked).
**Category:** workflow
