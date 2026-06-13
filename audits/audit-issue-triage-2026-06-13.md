# Open-Issue Triage — 2026-06-13

After closing 39 auto-generated "Morning digest" noise issues, **92 open / 89 real**
(3 residual auto-noise). Most are epic + sub-issue breakdowns from past
`prd-to-issues` runs; many shipped via the June 10–12 sprint but were never closed.
Buckets + dispositions below. Verified items are marked ✓.

## A. Close now — stale / superseded

- **#1 "CRITICAL: automation_engine.py truncated to 29 bytes"** — ✓ STALE. File is
  restored (1458 bytes, imported + functional). **Closing this in this pass.**
- **onboarding-v2 epic (#128–142)** — superseded by merged "Signup overhaul" (#235)
  + welcome thread/web-push/PWA waves (#250/#254). `SignupPage.jsx` ✓ present.
  Verify each sub-issue's file landed, then close the epic. Likely 80% done.
- **ops-automation epic (#114–127)** — `activity.py` ✓ present; activity logging
  shipped. Remaining real gap = **#213** (activity_log parity for all 4 automations).
  Close the rest after per-file confirmation.
- **memory-hygiene (#68–70)** — PRs #72/#73/#74 exist for these. Confirm merged → close.

## B. Stranded in PR #212 (do not re-file — track via #212 re-application)

- **#214** WordPress plugin · **#215** integration-health probe · **#216** vertical
  qualifier rubrics (the moat) · **#213** activity parity · **#217** Stripe Connect
  (also blocked on billing-architecture decision).
- These live on the gap-3 branch with **unrelated history** to main (see
  `audit-pr212-merge-readiness`). They land via surgical re-application, not a merge.

## C. Actionable now — concrete bugs/perf/security (highest value, small, verified files)

| # | What | File (✓ exists) |
|---|---|---|
| #99 | Stripe `SignatureVerificationError` catch anti-pattern masks handler errors | `routers/billing.py` |
| #94 | IndexError crash in `guard_checkout_for_fraud` (charges empty) | `services/fraud_guard.py` ✓ |
| #93 | fraud_guard flags `no_payment_required` as fraud | `services/fraud_guard.py` ✓ |
| #98 | `_find_tenant_by_phone` full-table scan, O(N) per inbound | `routers/twilio_webhooks.py` ✓ |
| #97 | `_chat_rate_limit` swallows exceptions → rate-limit silently off | `routers/widget_chat.py` ✓ |
| #107 | zapier `_get_api_key_client` missing plan_status check | zapier router |
| #112 | N+1 in `email_sequences` list endpoints | `routers/email_sequences.py` |
| #113 | dedupe `process_sequences` HTTP endpoint vs runner | sequences |
| #206 | timingSafeEqual for X-Agent-Token in agent-service | `agent-service/src` |
| #110 | wire lead-qualifier golden eval to CI | CI |
| #194 | em-dash violations blocking Item A (`check_project_invariants`) | UI copy |

Best ROI once CI is restored: the security/billing trio **#99, #94, #93** (live
payment path), then **#97/#98** (silent-failure + perf on inbound).

## D. Roadmap epics — not started (product decisions, not cleanup)

- photo-quote (#37–47, spec exists) · drive-kb (#49–56) · zapier CRM export
  (#59–64, partial — PR #71 docs) · self-maintenance (#143–154) · managed-agents
  rollout (#33) · landing hero snapshot test (#34).
- Keep open; these are backlog, not debt. Prioritize against launch goals separately.

## Recommended order
1. Close bucket A after per-file confirmation (kills ~30 stale issues).
2. Restore CI (external blocker), then sweep bucket C bugs — small, high-value.
3. Re-apply bucket B via #212 surgical slices.
4. Schedule bucket D against launch priorities.

## Note on the noise source
The digest issues (39 closed today) regenerate from a **local scheduled `/morning`
automation**, not a repo workflow. Cap it at the scheduler to stop the bleed.
