# AgentNexLiFy — Launch Readiness Rubric

**Purpose:** Decide go / no-go for paid launch via evidence, not gut. Partners + engineer run this together. Rescore monthly until shipped.

**How to score:** Each criterion 0 / 1 / 2. Multiply by weight. Sum per dimension. Sum dimensions. Compare vs threshold.

- **0** — not done, or known broken
- **1** — partial, works for happy path, gaps exist
- **2** — done, tested, documented

**Go threshold:** ≥ 210 / 262 AND zero criterion scoring 0 in a HIGH-severity dimension (2, 3, 10).

**Last scored:** 2026-04-21 (evidence refresh after contractor-wedge copy pass, MTOptions live measurement, public health burst load sample, refund-policy docs, and widget AI-disclosure update).

---

## Dimension 1 — Legal & compliance (weight: 3)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Terms of service drafted + linked in signup | 2 | `frontend/src/pages/TermsOfService.jsx` (10.5KB); SignupPage.jsx:327 links `/terms`. Legal review unknown `[partner-verify]` |
| 1.2 | Privacy policy drafted + covers tenant data + PII + AI | 2 | `frontend/src/pages/PrivacyPolicy.jsx` (14.7KB); SignupPage.jsx:328 links `/privacy` |
| 1.3 | GDPR / CCPA data deletion endpoint works | 0 | No `/api/v1/.../delete-account` endpoint found; no GDPR SAR flow |
| 1.4 | Cookie/consent banner present where required | 0 | No cookie banner component in `frontend/src/` |
| 1.5 | Business entity registered (LLC / C-corp) + bank + EIN | ? | `[partner-verify]` |
| 1.6 | Merchant agreement signed (Stripe Connect or direct) | 1 | Stripe live keys active per webhook code. Signed agreement `[partner-verify]` |
| 1.7 | Written AI-disclosure in widget greeting ("powered by AI") | 2 | `widget/agentnexlify-widget.js` now prepends AI disclosure at runtime when the saved greeting lacks it; `frontend/src/utils/businessPresets.js` seed copy also now identifies the assistant as AI. |
| 1.8 | DPAs available for customers who ask | 0 | No DPA template in `docs/` |

**Subtotal:** 7 / 16 × 3 = **21 / 48** (1.5 + 1.6 unknown → scored conservative)

---

## Dimension 2 — Security (weight: 3, HIGH severity)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 2.1 | Multi-tenant isolation verified (RLS on every table OR tenant_id filter on every query) | 2 | `backend/services/tenant_scope.py` helpers enforce client_id/tenant_id scoping; regression guards in `tests/test_backend_regressions.py` |
| 2.2 | SSRF blocked on all outbound HTTP | 2 | ✓ 2026-04-13 (bug-patterns.md) |
| 2.3 | Webhook signature verification on inbound | 2 | Stripe: `billing.py:116`, `stripe_webhooks.py:40`; Twilio: `twilio_webhooks.py:33`; Resend (svix): `resend_webhooks.py:25` |
| 2.4 | All secrets in env vars, zero in git history | 2 | Pre-commit hook scans; `.env*` gitignored; no leaks in recent audits |
| 2.5 | Auth rate-limited on /login, /signup, /reset | 2 | `backend/routers/auth.py:450,479,695,734,803` — `@limiter.limit("5/minute")` |
| 2.6 | JWT rotation + refresh flow tested | 1 | JWT auth exists (auth.py) but refresh rotation test coverage unknown |
| 2.7 | Pen test OR automated security scan run (semgrep, snyk) | 1 | `.github/workflows/pr-check.yml` now installs Semgrep and runs `semgrep scan --config auto`. Local 2026-04-20 scan completed under Python 3.12 with UTF-8 enabled and surfaced 50 existing findings that still need triage. |
| 2.8 | Incident response playbook written | 2 | `docs/incident-response-playbook.md` defines severity, roles, first-15-minute containment, recovery, comms cadence, security rules, and post-incident aftercare. |

**Subtotal:** 14 / 16 × 3 = **42 / 48** — no HIGH-severity zeros in this dimension

---

## Dimension 3 — Billing & revenue integrity (weight: 3, HIGH severity)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 3.1 | Stripe webhook idempotency tested (replay same event twice) | 2 | ✓ 2026-04-17 (commit `8b9dc7b`) — `tests/test_stripe_webhook.py:388` observable-state assertion |
| 3.2 | Failed-payment dunning flow tested end-to-end | 1 | `tests/test_launch_risk_guardrails.py:75-105` covers `invoice.payment_failed`, persists `billing_dunning_attempt_count`, records the dunning event, and sends email. Still not a full webhook/scheduler integration path. |
| 3.3 | Proration on upgrade / downgrade tested | 1 | Stripe handles via API; no regression test |
| 3.4 | Cancellation preserves access until period end | 1 | `billing.py:341` allows `canceled` status; period-end preservation untested |
| 3.5 | Usage metering matches Stripe meter events ±1% | 1 | `monthly_conversation_limit` tracked; reconciliation not automated |
| 3.6 | Refund flow tested (partial + full) | 1 | `tests/test_launch_risk_guardrails.py:114-270` covers refund creation, idempotent replay, and audit-insert fallback. Partial/full refund matrix is still not explicitly exercised. |
| 3.7 | Trial → paid transition tested across all plans | 1 | `free_trial_started_at` tracked (auth.py:898); transition test coverage partial |
| 3.8 | Invoice generation reconciles against Stripe dashboard | 1 | `invoices` table + `generate_invoice`; reconciliation cron missing |

**Subtotal:** 9 / 16 × 3 = **27 / 48** — no HIGH-severity zeros in this dimension

---

## Dimension 4 — Observability (weight: 2)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 4.1 | Error alerts fire within 5 min of prod error | 1 | Railway → Slack wired, needs `RAILWAY_TOKEN` per notes |
| 4.2 | Sentry or equivalent captures unhandled exceptions | 1 | Sentry MCP plugin installed; OAuth pending |
| 4.3 | Uptime monitor (external) with SLO ≥ 99.5% | 0 | No external monitor (UptimeRobot/Pingdom/BetterUptime) configured |
| 4.4 | Key business metrics on a dashboard | 1 | AdminAnalyticsPage.jsx exists; MRR/churn coverage partial |
| 4.5 | Log retention ≥ 30 days | 0 | Railway default 7d; no log sink configured |
| 4.6 | Database advisor warnings all resolved | 2 | ✓ Zero as of 2026-04-09 (memory) |

**Subtotal:** 5 / 12 × 2 = **10 / 24**

---

## Dimension 5 — Load & capacity (weight: 2)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 5.1 | Load test run at 10× expected concurrent (p95 < 1s) | 1 | `ops/evals/run_public_health_load.py` + `ops/evals/public-health-load-2026-04-21.md` establish a reproducible external burst check (100 requests, concurrency 10, p95 291.2 ms). Still not a widget/chat-specific load test. |
| 5.2 | Database connection pool sized + tested | 1 | Supabase pool default; not tuned or tested |
| 5.3 | Claude API rate limits understood + surfaced to user | 1 | SDK handles 429; no tenant-facing surface |
| 5.4 | Widget render verified on slow 3G (Lighthouse PWA test) | 0 | Chrome install pending |
| 5.5 | Runaway-cost kill switch (per-tenant usage cap) | 2 | `backend/services/ai_usage_guard.py` enforces alert and hard-limit thresholds by tenant, `tests/test_launch_risk_guardrails.py` covers the plan baselines, and `docs/dev-knowledge/schema-log.md` documents the live support tables. |

**Subtotal:** 5 / 10 × 2 = **10 / 20**

---

## Dimension 6 — Data integrity (weight: 2)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 6.1 | Daily automated backup verified restorable | 1 | Supabase daily backups; restore drill not performed |
| 6.2 | Schema migrations numbered + forward-only | 2 | ✓ `docs/dev-knowledge/schema-log.md:730-753` documents migrations 106/107 applied on 2026-04-19, keeping the guardrail schema log current. |
| 6.3 | Pre-commit blocks dropped-column queries | 2 | ✓ CHECK 8 enforced (pre-commit hook) |
| 6.4 | Integration tests cover critical tables | 2 | ✓ `test_backend_regressions.py` — 12 passing (post-fix today) |
| 6.5 | PII minimization — no unnecessary customer data stored | 1 | `data_minimization: true` policy flag in support skill; no audit done |

**Subtotal:** 8 / 10 × 2 = **16 / 20**

---

## Dimension 7 — Support & onboarding (weight: 1)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 7.1 | Help docs / knowledge base accessible to customers | 1 | `knowledge-base/wiki/` internal; no public docs site |
| 7.2 | Support email monitored within 24h | ? | `[partner-verify]` — assumed 1 |
| 7.3 | Onboarding wizard completes without manual intervention | 1 | `frontend/src/pages/OnboardingWizardPage.jsx` exists; no auto-completion test |
| 7.4 | Cancel-flow is self-serve (no email required) | 1 | `frontend/src/pages/BillingPage.jsx` has cancel UI; churn capture missing |
| 7.5 | Status page exists | 0 | No status page (status.agentnexlify.com not configured) |

**Subtotal:** 4 / 10 × 1 = **4 / 10**

---

## Dimension 8 — Brand & positioning (weight: 1)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 8.1 | Landing page states price + plan + ICP clearly | 2 | `Home.jsx` pricing section + marketing-first hero (shipped today `9d27e2e`) |
| 8.2 | Demo widget embedded on landing works | 2 | `frontend/index.html:39-51` widget script tag with data-api-key |
| 8.3 | Tagline / elevator pitch agreed by all partners | 1 | "AI that helps run your business" set in OG today; partner sign-off `[partner-verify]` |
| 8.4 | Competitor FAQ (vs GoHighLevel, Drillbit, Podium) | 1 | `knowledge-base/wiki/competitors/` internal only; no customer-facing FAQ page |
| 8.5 | Case study or design-partner logo visible | 0 | 5 active testers (MTOptions top); no public case study / logo strip |

**Subtotal:** 6 / 10 × 1 = **6 / 10**

---

## Dimension 9 — Sales infrastructure (weight: 1)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 9.1 | Inbound lead capture on marketing site | 2 | `Contact.jsx` form + `widget_lead.py` + embedded widget on landing |
| 9.2 | Outbound email domain warmed + SPF/DKIM/DMARC clean | 1 | Resend DNS pending per rubric note |
| 9.3 | Pricing page A/B test wired (Growthbook / equiv) | 1 | `ABTestsPage.jsx` exists; pricing-specific test unclear |
| 9.4 | Referral / affiliate tracking | 1 | `admin_promotions.py:27` referral type exists; tracking flow partial |
| 9.5 | Cold-outreach templates + partner assignment | 0 | No outreach template set or partner assignment rules |

**Subtotal:** 5 / 10 × 1 = **5 / 10**

---

## Dimension 10 — Risk mitigation (weight: 2, HIGH severity)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 10.1 | Refund policy documented + honored | 2 | `frontend/src/pages/TermsOfService.jsx` now documents refund handling and request timing, `frontend/src/pages/BillingPage.jsx` surfaces the support path, and `docs/ops/refund-runbook.md` documents the operational refund flow. |
| 10.2 | Fraud rules: velocity limits, disposable-email block, CC mismatch | 0 | No fraud detection middleware found |
| 10.3 | Churn reason captured on cancel | 2 | `tests/test_launch_risk_guardrails.py:279-316` persists `cancellation_reason`, and `docs/dev-knowledge/schema-log.md:738-739` documents `tenant_cancellation_events` in migration 106. |
| 10.4 | Bus-factor: more than one person can deploy | 0 | Solo engineer per CLAUDE.md; partners non-engineer |
| 10.5 | Dead-man switch: if founder disappears, customers keep service for 30d | 1 | `docs/ops/service-continuity-plan.md` now documents the minimum access inventory and safe partner actions. Still needs credential distribution and real partner rehearsal. |
| 10.6 | Insurance (E&O / cyber) quoted | ? | `[partner-verify]` — assumed 0 |

**Subtotal:** 5 / 12 × 2 = **10 / 24** — ⚠️ **3 HIGH-severity zeros (10.2, 10.4, 10.6)**

---

## Scorecard — 2026-04-20

| Dimension | Raw | Weighted | Max | HIGH zeros |
|-----------|-----|----------|-----|------------|
| 1. Legal | 7 / 16 | 21 | 48 | — |
| 2. Security | 14 / 16 | 42 | 48 | — |
| 3. Billing | 9 / 16 | 27 | 48 | — |
| 4. Observability | 5 / 12 | 10 | 24 | — |
| 5. Load | 5 / 10 | 10 | 20 | — |
| 6. Data integrity | 8 / 10 | 16 | 20 | — |
| 7. Support | 4 / 10 | 4 | 10 | — |
| 8. Brand | 6 / 10 | 6 | 10 | — |
| 9. Sales | 5 / 10 | 5 | 10 | — |
| 10. Risk | 5 / 12 | 10 | 24 | **10.2, 10.4, 10.6** |
| **TOTAL** | — | **151** | **262** | **3 HIGH zeros** |

**Score:** 151 / 262 = **57.6%**

## Verdict — 2026-04-21

🔴 **NO-GO for paid launch.** Stay in design-partner mode.

- Below 160/262 soft-launch threshold (151)
- Below 210/262 go threshold (151)
- **3 HIGH-severity zeros** remain in Dimension 10 — any single one still blocks ship

## Highest-leverage next moves (ordered by leverage per hour)

Per Q4 of the rubric's meeting questions:

1. **Dim 10 (Risk) — 10/24 weighted.** The remaining hard blockers are now fraud rules, second-deployer readiness, and an insurance quote. Refund policy and continuity documentation are no longer the fastest wins because they already landed.
2. **Dim 5 (Load) — 10/20 weighted.** The public health burst check is now in place, but the next real lift is a widget/chat-specific load test with a disposable tenant and log review.
3. **Dim 1 (Legal) — 21/48 weighted.** GDPR deletion endpoint and cookie/consent remain open. AI disclosure no longer belongs on the blocker list.
4. **Dim 3 (Billing) — 27/48 weighted.** Refund flow exists, but partial/full refund coverage, proration coverage, and access-until-period-end evidence still need tightening.
5. **Dim 2 (Security) — 42/48 weighted.** Semgrep triage remains worthwhile, but it is no longer the clearest score-per-hour path compared with the three remaining risk zeros.

## Fastest path to "soft launch" (160/262 threshold)

Need **+9 weighted** and zero remaining HIGH-severity zeros.

Fastest credible path:

- Dim 10 fraud rules, second-deployer readiness, and insurance quote
- Dim 5 widget/chat-specific load test
- Dim 1 GDPR deletion endpoint or cookie/consent coverage

Total: **+9 weighted** plus the three HIGH-zero closures → soft launch unlocked (invite-only).

Still NO-GO for full paid launch until 210/262 AND zero HIGH zeros.

---

## Partner-verify items (can't score from code)

- 1.5 Business entity registered
- 1.6 Merchant agreement signed
- 7.2 Support email SLA
- 8.3 Tagline agreed
- 10.6 Insurance quoted

---

## 5 questions to answer every launch-review meeting

1. **What happens at 10× current traffic?** Name the specific thing that breaks first. If you don't know, run the load test.
2. **How do we know if we lose a customer's data?** Name the alert, the person paged, the time to detect.
3. **Which criterion scored 0 this cycle that would be fatal in prod?** If any HIGH-severity 0 exists → no-go regardless of total.
4. **What's the single highest-leverage item to raise our score most per hour of work?** Do it first next cycle.
5. **Did any criterion regress since last cycle?** If yes, why, and what's the preventive control.

---

## Decision rules

- **Go:** score ≥ 210 AND zero 0-scores in HIGH dims → ship paid plans.
- **Soft launch:** 160–210 AND zero 0-scores in HIGH dims → invite-only / design-partner pricing only.
- **No-go:** < 160 OR any 0-score in HIGH dim → keep in design-partner mode, do not take new paid revenue.

**Current state: NO-GO.**

## Cadence

Rescore monthly while pre-launch. After launch, rescore quarterly + on any HIGH-severity incident.

## Who scores what

- Dimensions 1, 3, 7, 8, 9 → partners (non-engineer tasks)
- Dimensions 2, 4, 5, 6 → engineer (Aidan)
- Dimension 10 → partners + engineer jointly

## Artifacts required when scoring 2

Each 2-score needs a linked artifact — test run, PR, URL, doc. "I think we did this" does not count.
