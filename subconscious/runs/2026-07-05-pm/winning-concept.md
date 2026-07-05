# Winning Concept — 2026-07-05-pm (Run 80)

## Recommendation

Add Step 9C to `.claude/skills/nightly-commit-review/SKILL.md` — automated brain connector health detection that reads `brain/INGESTION-LOG.md` nightly, detects 3+ consecutive failures, and creates a GH issue with `human-action-required` label.

## Why This, Why Now

The brain connectors have been broken for 5 consecutive days (GitHub 403 + SUPABASE_ACCESS_TOKEN missing, July 1-5). Run 80 mandate fires explicitly from run 79 `winning-concept.md §Run 80 Mandate`. Without Step 9C, the next round of failures would again go undetected for days — stale brain degrades all autonomous agents silently. Steps 9A and 9B (Moratorium Escalation Protocol and healthz maintenance) were both delivered in 1 nightly cycle using the same mechanism, proving the pattern reliable.

## Implementation Sketch

Add the following block to `.claude/skills/nightly-commit-review/SKILL.md` in the "Scheduled Task Prompt" section, after Step 9B:

```
### Step 9C — Brain Connector Health Check

Read `brain/INGESTION-LOG.md`. Scan the last 6 log entries (approx. last 3 refresh cycles). Count lines containing `error —` or `skipped —` in the most recent 3 date-stamped entries.

If count >= 3 (3+ consecutive failures across both connectors):
1. Create a GH issue with these exact fields:
   - Title: "brain: connector failures detected — GitHub 403 + SUPABASE_ACCESS_TOKEN (N consecutive days)"
   - Labels: human-action-required, operational
   - Body: paste the last 6 INGESTION-LOG lines, then: "Fix: (1) Rotate GitHub token with repo+issues read scope in Railway/GitHub Secrets. (2) Set SUPABASE_ACCESS_TOKEN = <service_role_key> in Railway Variables. (3) Verify: run `python brain/_tools/refresh_connectors.py` and check INGESTION-LOG.md for success markers."
2. Log "Step 9C: GH issue created (N consecutive failures)" to the nightly report.
3. Do NOT create a duplicate issue if one with `human-action-required` + `operational` labels is already open from a prior Step 9C run.

If count < 3: Log "Step 9C: brain connectors healthy or failure < 3-cycle threshold. No action."
```

## What This Replaces

Previous active direction: "Fix brain connector credentials — GitHub 403 + SUPABASE_ACCESS_TOKEN missing (run 79 winner)" — that item is still pending_human. This is additive: Step 9C provides ongoing detection for future failures; run 79 fix addresses the current one.

## Confidence

HIGH — mandate fires, AUTONOMOUS-EXECUTABLE (same class as Steps 9A+9B, both delivered in 1 nightly cycle), implementation sketch is concrete, dedup guard prevents alarm fatigue.

---

## Bonus Action A: Create ops/monitoring/SETUP.md

Once nightly Step 9B writes `ops/monitoring/healthz-alert.sh`, create `ops/monitoring/SETUP.md` documenting:
- What `SLACK_ALERT_WEBHOOK_URL` is (Slack incoming webhook URL)
- How to create: Slack → Your workspace → Apps → Incoming Webhooks → Add to Slack
- Where to set: Railway project → Variables tab → `SLACK_ALERT_WEBHOOK_URL = <webhook-url>`
- How to verify: trigger a test call to the webhook URL with `curl -X POST -d '{"text":"test"}' <url>`
- AUTONOMOUS-EXECUTABLE (pure markdown), complements the healthz-alert chain.

## Bonus Action B: SMS Compliance Dashboard GH Issue

File GH issue with:
- Title: `feat(sms): SMS Compliance Dashboard — GET /api/sms/compliance/summary + SmsCompliance.jsx`
- Labels: `ai-ready`, `customer-value`, `frontend`, `backend`  
- Body: paste full code from `subconscious/runs/2026-06-30-pm/winning-concept.md` (backend router, React page, exact edits for `main.py`, `App.jsx`, `Sidebar.jsx`)
- Invariants reminder: `client_id not tenant_id`, no `from __future__ import annotations`, mask phone to last 4 digits in API response
- For issue-to-pr-loop autonomous execution

---

## Run 81 Mandate

If `brain/INGESTION-LOG.md` still shows failures after run 81: Step 9C should have fired and created a GH issue automatically. Verify that GH issue exists. If Step 9C itself failed to deploy (nightly didn't add it): escalate with explicit human instruction to add Step 9C manually (2 min copy-paste into SKILL.md).

If `SLACK_ALERT_WEBHOOK_URL` still not set: document in SETUP.md as confirmed known gap, no further automated mandate.

---

## Verification

```
Verified: brain/INGESTION-LOG.md 5 consecutive failures confirmed — PASS
Verified: run 80 mandate fires (run 79 winning-concept.md §Run 80 Mandate) — PASS
Verified: Step 9A/9B precedent (both AUTONOMOUS-EXECUTABLE, both 1-cycle delivery) — PASS
Verified: ops/monitoring/ contains only uptime-checks.json (healthz-alert.sh absent) — PASS
Verified: check_project_invariants.py exits 1 on widget drift only (retired topic) — PASS
Verified: No SmsCompliance.jsx in frontend/src/pages/ — PASS (no change from prior runs)
```
