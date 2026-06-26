# Council Fixes — Issue Register (2026-06-25)

Tracked fixes from the LLM Council audit + owner synthesis
(`docs/dev-knowledge/council-onboarding-integration-2026-06-25.md`).
Status legend: TODO / IN-PROGRESS / DONE / OPS (needs business/console action, not code).

| # | Issue | Severity | Status | Where |
|---|-------|----------|--------|-------|
| 1 | **SMS compliance guardrails** — no STOP/opt-out, consent ledger, or quiet hours on the SMS path (TCPA $500–1500/text). | CRITICAL / legal | DONE | `os_actions/sms.py`, `twilio_webhooks.py`, `os_inbound.py`, new `sms_compliance.py`, migration 160 |
| 2 | **Missed-call text-back never run in prod** (0 sends); 10DLC/A2P registration dependency. | HIGH | OPS + verify | `voice_recovery.py`, Twilio console (10DLC) |
| 3 | **Crawl-the-site onboarding wow + GBP/Facebook fallback** for no-website businesses. | HIGH (activation) | TODO | onboarding/crawl + new fallback |
| 4 | **Money-language dashboard** — leads captured / pipeline $ / missed-calls recovered; conversation "score" → temperature (🔥/👀/spam). | HIGH (value perception) | DONE | `frontend/src/utils/leadTemperature.js` + LeadsPage/ClientList/LeadDetailDrawer; OverviewCards already outcome-framed |
| 5 | **Per-recipient SMS frequency cap** (margin + anti-spam on $19.99 tier). | MED | DONE | `sms_compliance.recently_messaged` + `twilio_webhooks.py` |
| 6 | **Integration health alerts** — OAuth lapse / widget-not-firing surfaced to owner, not swallowed. | MED | DONE | `frontend/src/pages/Dashboard/IntegrationHealthBanner.jsx` consuming existing `/api/v1/integrations/health` |
| 7 | **Propose-only data cleaning** — never auto-merge/auto-edit customer or financial records; review queue + audit + rollback. | MED (trust) | TODO (design) | data-clean feature (not yet built) |
| 8 | **Positioning: hide "8 agents", sell outcomes** — "Never Miss a Lead" (T1) / "AI Office Manager" (T2). | MED (GTM) | DONE (copy) | `Home.jsx`, `WizardStepEmbed.jsx` reframed to outcomes |
| 9 | **Concierge → self-serve guided wizard** (parallel build). | LOW now | OPS/TODO | onboarding wizard |

## Fix notes
- **#1 (this pass):** new `sms_compliance.py` (opt-out check + inbound STOP/START classify + quiet-hours), migration `160_sms_opt_outs`, gate every tenant-aware send path, inbound STOP handler in `os_inbound.py`, tests. Reuses existing `tenants.textback_quiet_start/end` columns and `sms_rate_limiter` daily cap.
- **#2:** code exists; needs a real end-to-end prod test on a 10DLC-registered number before demo/sale. Console/ops.
- **#8 (DONE, copy):** landing-page + wizard no longer count agents ("Eight AI agents. One manager." / "team of 8 AI agents" / "8 AI department heads"). Now sells the outcome — "An AI office manager that runs the busywork for you" + per-capability outcomes (follows up with every lead, chases unpaid invoices, you approve before anything sends). Brand names "AI Front Desk" / "AI Workforce" kept; renaming the tiers to "Never Miss a Lead" / "AI Office Manager" remains an owner marketing call.
- **#9:** business/onboarding-process decision; see ops checklist below.
- **#4 (DONE):** new `leadTemperature(score)` util maps 0-10 or 0-100 numeric score to 🔥 Ready to book / 👀 Just looking / ❄️ Cold / New(null). Applied in LeadsPage table, ClientList table, LeadDetailDrawer qualifier + score panel. Emoji in these owner-facing badges is an intentional override of `frontend-patterns.md` anti-slop emoji ban — council asked for glanceable temperature for non-technical owners. Dashboard `OverviewCards` already used money/outcome language (Leads Captured, Missed Calls This Week + "auto text-back sent"); pipeline-$ deferred (needs backend deal-value field).
- **#6 (DONE):** dashboard-level `IntegrationHealthBanner` calls the existing `/api/v1/integrations/health` aggregate and shows a red/amber alert ONLY for connections that were set up and lapsed (detail != "not configured"). Closes the "swallowed lapse" gap without nagging chatbot-tier owners about providers they never connected. Pure `actionableIntegrationAlerts()` filter unit-tested. The richer per-provider view already lived in `IntegrationHealthDashboard.jsx`; this surfaces it proactively.
- **#3/#7:** real features.

Updated as fixes land. See git log for commits referencing this register.
