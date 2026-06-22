# Launch-Readiness — Remaining Work by Owner (2026-06-22)

Companion to `planning/launch-readiness-rubric.md` (221/262 at the 2026-06-10
rescore). This sorts every sub-2 criterion by **who can actually close it**.

**Finding:** after closing **9.5** (cold-outreach templates — `planning/outreach-templates.md`,
this session), there are **no remaining pure-engineering items**. Everything left
needs a partner, legal, ops, or external-service action — none of it is code.
The sole HIGH-severity blocker for paid launch is **10.6 (insurance)**, a partner task.

## ENG (code) — status
All code criteria were swept 2026-06-10; 9.5 closed this session. **Nothing left
for engineering to write.** Re-run the rubric only when a partner/ops item lands.

## PARTNER / LEGAL (owner: partners)
| # | Item | Action to reach 2 |
|---|------|-------------------|
| 1.5 | Business entity (LLC/EIN/bank) | Register + record evidence |
| 1.6 | Merchant agreement signed | Sign Stripe/merchant agreement |
| 1.8 | DPAs available | Counsel review of `docs/legal/dpa-template.md` |
| 7.2 | Support email monitored <24h | Confirm monitoring + SLA owner |
| 8.3 | Tagline sign-off | All partners agree the elevator pitch |
| 8.5 | Case study / logo | Get 1 design-partner (MTOptions) to a public quote/logo |
| **10.6** | **Insurance (E&O / cyber)** | **Get a quote — only HIGH-severity blocker** |
| 10.4 | Bus-factor: 2+ can deploy | Real deploy rehearsal by a second person |
| 10.5 | Dead-man 30-day continuity | Distribute credentials + partner rehearsal |

## OPS / EXTERNAL SERVICE (owner: ops)
| # | Item | Action to reach 2 |
|---|------|-------------------|
| 4.1 | Error alerts <5 min | Set `RAILWAY_TOKEN` + `SLACK_ALERT_WEBHOOK_URL` (workflow already wired; throttled to /4h in #348 — re-point to Sentry for real-time) |
| 4.2 | Sentry unhandled-exception capture | Complete Sentry OAuth/DSN wiring |
| 4.3 | External uptime SLO ≥99.5% | Move off GitHub Actions to UptimeRobot/BetterUptime (see `docs/ci-minute-budget.md`); SLO history |
| 4.5 | Log retention ≥30d | Configure a log sink (Railway → external); Railway default is 7d |
| 6.1 | Backup restore verified | Run the Supabase dashboard restore-to-new-project step in `docs/ops/restore-drill-2026-06-10.md` |
| 9.2 | Email SPF/DKIM/DMARC | Finish Resend DNS records |

## EXTERNAL SERVICE (owner: ops, needs a vendor)
| # | Item | Action to reach 2 |
|---|------|-------------------|
| 7.5 | Status page | Stand up `status.agentnexlify.com` (BetterUptime/Instatus) fed by the uptime monitor |

## Sales content (owner: BD — partially eng-assisted)
| # | Item | Status |
|---|------|--------|
| 9.5 | Cold-outreach templates + partner assignment | **DONE 2026-06-22** — `planning/outreach-templates.md` |

---

### Bottom line
Engineering's launch-readiness backlog is **clear**. The path to a clean paid
launch now runs entirely through partner/ops/legal actions, with **insurance
(10.6)** as the single HIGH-severity gate. Recommend the partners take the
PARTNER/LEGAL table as their punch-list and ops the OPS table; re-score the
rubric as each lands.
