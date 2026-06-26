# Council Fixes — Issue Register (2026-06-25)

Tracked fixes from the LLM Council audit + owner synthesis
(`docs/dev-knowledge/council-onboarding-integration-2026-06-25.md`).
Status legend: TODO / IN-PROGRESS / DONE / OPS (needs business/console action, not code).

| # | Issue | Severity | Status | Where |
|---|-------|----------|--------|-------|
| 1 | **SMS compliance guardrails** — no STOP/opt-out, consent ledger, or quiet hours on the SMS path (TCPA $500–1500/text). | CRITICAL / legal | DONE | `os_actions/sms.py`, `twilio_webhooks.py`, `os_inbound.py`, new `sms_compliance.py`, migration 160 |
| 2 | **Missed-call text-back never run in prod** (0 sends); 10DLC/A2P registration dependency. | HIGH | OPS + verify | `voice_recovery.py`, Twilio console (10DLC) |
| 3 | **Crawl-the-site onboarding wow + GBP/Facebook fallback** for no-website businesses. | HIGH (activation) | TODO | onboarding/crawl + new fallback |
| 4 | **Money-language dashboard** — leads captured / pipeline $ / missed-calls recovered; conversation "score" → temperature (🔥/👀/spam). | HIGH (value perception) | TODO | `frontend/src/pages/Dashboard.jsx` + lead card |
| 5 | **Per-recipient SMS frequency cap** (margin + anti-spam on $19.99 tier). | MED | DONE | `sms_compliance.recently_messaged` + `twilio_webhooks.py` |
| 6 | **Integration health alerts** — OAuth lapse / widget-not-firing surfaced to owner, not swallowed. | MED | TODO | `tenant_health.py`, connection-status UI |
| 7 | **Propose-only data cleaning** — never auto-merge/auto-edit customer or financial records; review queue + audit + rollback. | MED (trust) | TODO (design) | data-clean feature (not yet built) |
| 8 | **Positioning: hide "8 agents", sell outcomes** — "Never Miss a Lead" (T1) / "AI Office Manager" (T2). | MED (GTM) | OPS + copy | frontend copy, marketing |
| 9 | **Concierge → self-serve guided wizard** (parallel build). | LOW now | OPS/TODO | onboarding wizard |

## Fix notes
- **#1 (this pass):** new `sms_compliance.py` (opt-out check + inbound STOP/START classify + quiet-hours), migration `160_sms_opt_outs`, gate every tenant-aware send path, inbound STOP handler in `os_inbound.py`, tests. Reuses existing `tenants.textback_quiet_start/end` columns and `sms_rate_limiter` daily cap.
- **#2:** code exists; needs a real end-to-end prod test on a 10DLC-registered number before demo/sale. Console/ops.
- **#8/#9:** business/marketing decisions + copy; not a single code fix.
- **#3/#4/#6/#7:** real features; #4 is the smallest and highest perceived-value, do next after #1.

Updated as fixes land. See git log for commits referencing this register.
