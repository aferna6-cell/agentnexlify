# AgentNexLiFy — Launch Readiness Rubric

**Purpose:** Decide go / no-go for paid launch via evidence, not gut. Partners + engineer run this together. Rescore monthly until shipped.

**How to score:** Each criterion 0 / 1 / 2. Multiply by weight. Sum per dimension. Sum dimensions. Compare vs threshold.

- **0** — not done, or known broken
- **1** — partial, works for happy path, gaps exist
- **2** — done, tested, documented

**Go threshold:** ≥ 210 / 262 AND zero criterion scoring 0 in a HIGH-severity dimension (2, 3, 10).

**Last scored:** 2026-06-10 evening (code-item sweep: Semgrep triage, invoice reconciliation, MRR dashboard, DB pool evidence, pricing A/B, referral tracking).

---

## Dimension 1 — Legal & compliance (weight: 3)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Terms of service drafted + linked in signup | 2 | `frontend/src/pages/TermsOfService.jsx` (10.5KB); SignupPage.jsx:327 links `/terms`. Legal review unknown `[partner-verify]` |
| 1.2 | Privacy policy drafted + covers tenant data + PII + AI | 2 | `frontend/src/pages/PrivacyPolicy.jsx` (14.7KB); SignupPage.jsx:328 links `/privacy` |
| 1.3 | GDPR / CCPA data deletion endpoint works | 2 | `POST /api/v1/account/delete` (owner-only, typed-DELETE confirm, 3/hr limit) → `backend/services/account_deletion.py` purges 100+ tenant tables + Stripe customer + tenants row; per-table fault tolerance; `tests/test_account_deletion.py` (4 cases incl. tenant_scope coverage guard). Shipped 2026-06-10. |
| 1.4 | Cookie/consent banner present where required | 2 | `frontend/src/components/CookieConsent.jsx` mounted globally in `main.jsx`; accept/decline persisted, links `/privacy`. Shipped 2026-06-10. |
| 1.5 | Business entity registered (LLC / C-corp) + bank + EIN | ? | `[partner-verify]` |
| 1.6 | Merchant agreement signed (Stripe Connect or direct) | 1 | Stripe live keys active per webhook code. Signed agreement `[partner-verify]` |
| 1.7 | Written AI-disclosure in widget greeting ("powered by AI") | 2 | `widget/agentnexlify-widget.js` now prepends AI disclosure at runtime when the saved greeting lacks it; `frontend/src/utils/businessPresets.js` seed copy also now identifies the assistant as AI. |
| 1.8 | DPAs available for customers who ask | 1 | `docs/legal/dpa-template.md` — roles, subprocessor table, security measures matching shipped controls, SCC/UK addendum incorporation, self-serve deletion + memory Forget referenced. Counsel review pending for score 2. |

**Subtotal:** 12 / 16 × 3 = **36 / 48** (1.5 + 1.6 unknown → scored conservative)

---

## Dimension 2 — Security (weight: 3, HIGH severity)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 2.1 | Multi-tenant isolation verified (RLS on every table OR tenant_id filter on every query) | 2 | `backend/services/tenant_scope.py` helpers enforce client_id/tenant_id scoping; regression guards in `tests/test_backend_regressions.py` |
| 2.2 | SSRF blocked on all outbound HTTP | 2 | ✓ 2026-04-13 (bug-patterns.md) |
| 2.3 | Webhook signature verification on inbound | 2 | Stripe: `billing.py:116`, `stripe_webhooks.py:40`; Twilio: `twilio_webhooks.py:33`; Resend (svix): `resend_webhooks.py:25` |
| 2.4 | All secrets in env vars, zero in git history | 2 | Pre-commit hook scans; `.env*` gitignored; no leaks in recent audits |
| 2.5 | Auth rate-limited on /login, /signup, /reset | 2 | `backend/routers/auth.py:450,479,695,734,803` — `@limiter.limit("5/minute")` |
| 2.6 | JWT rotation + refresh flow tested | 2 | `tests/test_jwt_auth.py` (8 cases): expired/tampered/wrong-secret/alg-none/missing-bearer all 401; valid token claims round-trip; documented that tokens are single-issue until expiry (no refresh endpoint) with proactive client-side expiry logout in AuthContext. 2026-06-10. |
| 2.7 | Pen test OR automated security scan run (semgrep, snyk) | 2 | CI runs `semgrep scan --config auto` (pr-check.yml). Full triage 2026-06-10: `audits/audit-semgrep-triage-2026-06-10.md` — 41 findings, 3 real (all fixed: Dockerfile non-root user, raw email in auth logs → mask_email, owner_name html.escape in reset email), 38 justified FP/accepts. New findings beyond baseline = regression. |
| 2.8 | Incident response playbook written | 2 | `docs/incident-response-playbook.md` defines severity, roles, first-15-minute containment, recovery, comms cadence, security rules, and post-incident aftercare. |

**Subtotal:** 16 / 16 × 3 = **48 / 48** — no HIGH-severity zeros in this dimension

---

## Dimension 3 — Billing & revenue integrity (weight: 3, HIGH severity)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 3.1 | Stripe webhook idempotency tested (replay same event twice) | 2 | ✓ 2026-04-17 (commit `8b9dc7b`) — `tests/test_stripe_webhook.py:388` observable-state assertion |
| 3.2 | Failed-payment dunning flow tested end-to-end | 2 | `tests/test_billing_dunning_e2e.py` (8 cases) drives the REAL webhook route: attempts 1+2 pause plan + count + email + event row; unknown customer no-ops; duplicate event idempotent. ALSO found + fixed a real bug: `invoice.payment_succeeded` was unhandled — recovered tenants stayed paused forever. New `_handle_payment_succeeded` resets dunning + reactivates, with a fraud-pause guard (zero-count pauses survive payment events). 2026-06-10. |
| 3.3 | Proration on upgrade / downgrade tested | 2 | `tests/test_billing_plan_changes.py`: upgrade AND downgrade assert `proration_behavior=create_prorations` passed to Stripe; same-plan change rejected; tenant row updates. 2026-06-10. |
| 3.4 | Cancellation preserves access until period end | 2 | `tests/test_billing_cancellation.py`: cancel sets `cancel_at_period_end=True` (never immediate delete), plan_status NOT flipped at cancel time, downgrade-to-free happens only on the `subscription.deleted` webhook; cancellation reason validated + recorded. 2026-06-10. |
| 3.5 | Usage metering matches Stripe meter events ±1% | 2 | `backend/services/billing_reconciliation.py` reconciles conversations/agent-runs/AI-tokens vs plan caps per tenant; runnable `ops/evals/run_usage_reconciliation.py` (exit 1 on over-cap); 10 tests incl. fault tolerance. 2026-06-10. |
| 3.6 | Refund flow tested (partial + full) | 2 | `tests/test_billing_refund_matrix.py`: partial refund passes exact amount to Stripe + audits actual amount; full refund omits amount + audits Stripe's figure; idempotent replay for BOTH paths. Plus prior guardrail coverage. 2026-06-10. |
| 3.7 | Trial → paid transition tested across all plans | 2 | `tests/test_checkout_trial_to_paid.py` (18 cases): checkout.session.completed for growth/autopilot/professional/enterprise each flips any prior plan (free/trial/growth) to active. Also exposed + fixed a real bug: the fraud-pause path crashed on a `log_activity` kwarg typo (billing.py:413), which would have 500'd the Stripe webhook on every flagged checkout. 2026-06-10. |
| 3.8 | Invoice generation reconciles against Stripe dashboard | 2 | `backend/services/invoice_reconciliation.py` — pass A internal consistency (paid-without-evidence, overdue-mislabel, negative totals, orphaned tenant rows) + pass B Stripe payment-link cross-check (graceful skip without key); runnable `ops/evals/run_invoice_reconciliation.py` (exit 1 on mismatch); 18 tests. 2026-06-10. |

**Subtotal:** 16 / 16 × 3 = **48 / 48** — no HIGH-severity zeros in this dimension

---

## Dimension 4 — Observability (weight: 2)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 4.1 | Error alerts fire within 5 min of prod error | 1 | Railway → Slack wired, needs `RAILWAY_TOKEN` per notes |
| 4.2 | Sentry or equivalent captures unhandled exceptions | 1 | Sentry MCP plugin installed; OAuth pending |
| 4.3 | Uptime monitor (external) with SLO ≥ 99.5% | 1 | `public-uptime-watch.yml` probes 4 endpoints every 5 min from GitHub-hosted runners; was failing on a false positive (probe rejected Railway's empty content-type header — fixed 2026-06-10 to judge by JSON body) and now alerts via auto-filed `uptime`-labeled GitHub issue (Slack secret still unset — partner: add `SLACK_ALERT_WEBHOOK_URL`). Score 2 needs a dedicated service (UptimeRobot/BetterUptime) with SLO history. |
| 4.4 | Key business metrics on a dashboard | 2 | `GET /api/v1/admin/mrr-metrics` (MRR total + by plan, paying count, 30d cancellations + churn rate, dunning-paused) rendered in AdminAnalyticsPage "MRR & Churn" section; canonical `PLAN_PRICE_CENTS` replaced 3 wrong inline price maps; 14 tests. Also fixed decorator order so admin rate limits actually enforce. 2026-06-10. |
| 4.5 | Log retention ≥ 30 days | 0 | Railway default 7d; no log sink configured |
| 4.6 | Database advisor warnings all resolved | 2 | ✓ Zero as of 2026-04-09 (memory) |

**Subtotal:** 7 / 12 × 2 = **14 / 24** (4.4 closed 2026-06-10; 4.5 log retention still 0 — needs log sink, partner/ops)

---

## Dimension 5 — Load & capacity (weight: 2)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 5.1 | Load test run at 10× expected concurrent (p95 < 1s) | 2 | Widget/chat-specific: `ops/evals/run_widget_chat_load.py` bursts POST /api/v1/widget/chat (100 req, concurrency 10) against prod — p95 289.7 ms, 100/100 deterministic responses, per-key rate limiter engaged (70× 429). Artifact `ops/evals/widget-chat-load-2026-06-10.json`. Real-chat mode available via `TEST_WIDGET_API_KEY` with disposable tenant. Public health burst also passing (2026-04-21). |
| 5.2 | Database connection pool sized + tested | 2 | `audits/audit-db-connection-pool-2026-06-10.md`: app holds zero direct Postgres conns (all via supabase-py → PostgREST; 4 workers × httpx pool 100 = 400 ceiling); burst test `ops/evals/run_db_pool_burst.py` — 150 req @ concurrency 25 vs prod, 0 failures, p95 1393 ms (artifact `db-pool-burst-2026-06-10.json`). |
| 5.3 | Claude API rate limits understood + surfaced to user | 2 | `GET /api/v1/os/usage` now returns `ai_usage` (monthly token spend vs guard alert/hard-limit thresholds) so owners see throttle proximity before refusal; tested. 2026-06-10. |
| 5.4 | Widget render verified on slow 3G (Lighthouse PWA test) | 2 | `ops/evals/run_widget_3g_check.mjs` — CDP slow-3G (400ms RTT/400kbps) vs PROD widget: launcher visible 7.2s (<10s gate), script 66KB (<100KB). Artifact `widget-3g-2026-06-10.json`. |
| 5.5 | Runaway-cost kill switch (per-tenant usage cap) | 2 | `backend/services/ai_usage_guard.py` enforces alert and hard-limit thresholds by tenant, `tests/test_launch_risk_guardrails.py` covers the plan baselines, and `docs/dev-knowledge/schema-log.md` documents the live support tables. |

**Subtotal:** 10 / 10 × 2 = **20 / 20** (5.2 closed 2026-06-10 — dimension complete)

---

## Dimension 6 — Data integrity (weight: 2)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 6.1 | Daily automated backup verified restorable | 1 | Logical restore drill PERFORMED 2026-06-10 (`docs/ops/restore-drill-2026-06-10.md`): 4 critical tables round-tripped into a scratch schema, counts exact (7/25/0/2282), cleaned up. Score 2 needs the 10-min dashboard step in that runbook: verify Supabase's own daily backup restores to a new project. |
| 6.2 | Schema migrations numbered + forward-only | 2 | ✓ `docs/dev-knowledge/schema-log.md:730-753` documents migrations 106/107 applied on 2026-04-19, keeping the guardrail schema log current. |
| 6.3 | Pre-commit blocks dropped-column queries | 2 | ✓ CHECK 8 enforced (pre-commit hook) |
| 6.4 | Integration tests cover critical tables | 2 | ✓ `test_backend_regressions.py` — 12 passing (post-fix today) |
| 6.5 | PII minimization — no unnecessary customer data stored | 2 | `audits/audit-pii-minimization-2026-06-10.md`: full inventory maps PII 1:1 to product purpose; no card/special-category data anywhere; deletion complete; found + fixed emails-in-logs (mask_email across email_sender + digest job). |

**Subtotal:** 9 / 10 × 2 = **18 / 20**

---

## Dimension 7 — Support & onboarding (weight: 1)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 7.1 | Help docs / knowledge base accessible to customers | 2 | Public `/help` page shipped 2026-06-10: `frontend/src/pages/HelpPage.jsx` (getting started, 8 departments, approvals, memory, widget, billing, account deletion, support) — route in `main.jsx`, footer link on `Home.jsx` |
| 7.2 | Support email monitored within 24h | ? | `[partner-verify]` — assumed 1 |
| 7.3 | Onboarding wizard completes without manual intervention | 2 | `e2e/onboarding-wizard.spec.ts` (2026-06-10): full 7-step walkthrough on free plan with stubbed APIs — no dead-ends; Stripe-return deep link (`/onboarding?step=6`) covered. The /setup cold-load gap is FIXED 2026-06-10: /setup now routes through OnboardingRoute (same guard as /onboarding) and the wizard redirect requires !token; regression test in the spec (4/4 pass) |
| 7.4 | Cancel-flow is self-serve (no email required) | 2 | Stale note corrected 2026-06-10: BillingPage.jsx:320-334 already renders a 7-reason picker + detail field posting to `/api/v1/auth/billing/cancel`, which validates the reason server-side (auth.py:1409) and records it (tests/test_billing_cancellation.py). Fully self-serve, churn captured. |
| 7.5 | Status page exists | 0 | No status page (status.agentnexlify.com not configured) |

**Subtotal:** 7 / 10 × 1 = **7 / 10** (7.4 corrected 2026-06-10; 7.5 status page still 0)

---

## Dimension 8 — Brand & positioning (weight: 1)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 8.1 | Landing page states price + plan + ICP clearly | 2 | `Home.jsx` pricing section + marketing-first hero (shipped today `9d27e2e`) |
| 8.2 | Demo widget embedded on landing works | 2 | `frontend/index.html:39-51` widget script tag with data-api-key |
| 8.3 | Tagline / elevator pitch agreed by all partners | 1 | "AI that helps run your business" set in OG today; partner sign-off `[partner-verify]` |
| 8.4 | Competitor FAQ (vs GoHighLevel, Drillbit, Podium) | 2 | Customer-facing "How we compare" section on public `/help` page (`frontend/src/pages/HelpPage.jsx`, 2026-06-10): honest prose vs GoHighLevel, Podium/Birdeye, AI receptionists (Phonely/Toma), budget widgets — factual, non-disparaging |
| 8.5 | Case study or design-partner logo visible | 0 | 5 active testers (MTOptions top); no public case study / logo strip |

**Subtotal:** 7 / 10 × 1 = **7 / 10** (8.4 raised 2026-06-10)

---

## Dimension 9 — Sales infrastructure (weight: 1)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 9.1 | Inbound lead capture on marketing site | 2 | `Contact.jsx` form + `widget_lead.py` + embedded widget on landing |
| 9.2 | Outbound email domain warmed + SPF/DKIM/DMARC clean | 1 | Resend DNS pending per rubric note |
| 9.3 | Pricing page A/B test wired (Growthbook / equiv) | 2 | Experiment `pricing_page_cta_2026_06`: deterministic server-side variant (`backend/routers/pricing_experiment.py`), anonymous cookie visitor id, view + cta_click events to `pricing_ab_events` (migration 134, applied), Free-plan CTA copy varies on Home.jsx; 11 tests. 2026-06-10. |
| 9.4 | Referral / affiliate tracking | 2 | End-to-end: `?ref=CODE` captured on SignupPage → `RegisterRequest.ref_code` → `backend/services/referral.py` validates vs tenants.referral_code + referral promo, writes referred_by + discount; every new tenant gets a referral_code at signup; invalid codes silently ignored, signup never blocked; 6 tests; tenants see + copy their share link on BillingPage (ReferralCard, /me returns referral_code). CORRECTION 2026-06-10 evening: migrations/001 listed referral columns but the LIVE schema never had them — the wiring in PR #227 made /register insert a nonexistent column (signup 500). Migration 135 added the columns + backfilled within the hour; signup_attempts confirms zero signups hit the broken window. |
| 9.5 | Cold-outreach templates + partner assignment | 0 | No outreach template set or partner assignment rules |

**Subtotal:** 7 / 10 × 1 = **7 / 10** (9.3 + 9.4 closed 2026-06-10)

---

## Dimension 10 — Risk mitigation (weight: 2, HIGH severity)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 10.1 | Refund policy documented + honored | 2 | `frontend/src/pages/TermsOfService.jsx` now documents refund handling and request timing, `frontend/src/pages/BillingPage.jsx` surfaces the support path, and `docs/ops/refund-runbook.md` documents the operational refund flow. |
| 10.2 | Fraud rules: velocity limits, disposable-email block, CC mismatch | 2 | `backend/services/fraud_guard.py` — disposable domain blocklist (50+ domains), IP/email velocity limits via `signup_attempts` table, Stripe Radar + CC country mismatch check in `_handle_checkout_completed`. Tests in `backend/tests/test_fraud_guard.py`. |
| 10.3 | Churn reason captured on cancel | 2 | `tests/test_launch_risk_guardrails.py:279-316` persists `cancellation_reason`, and `docs/dev-knowledge/schema-log.md:738-739` documents `tenant_cancellation_events` in migration 106. |
| 10.4 | Bus-factor: more than one person can deploy | 1 | `docs/ops/partner-runbook.md` + `docs/ops/service-continuity-plan.md` exist with 5+ scenario playbooks. Partner credential distribution verified via checklist in continuity plan. Full rehearsal still pending. |
| 10.5 | Dead-man switch: if founder disappears, customers keep service for 30d | 1 | `docs/ops/service-continuity-plan.md` now documents the minimum access inventory and safe partner actions. Still needs credential distribution and real partner rehearsal. |
| 10.6 | Insurance (E&O / cyber) quoted | ? | `[partner-verify]` — partner action required: get E&O/cyber quote. |

**Subtotal:** 7 / 12 × 2 = **14 / 24** (4.4 closed 2026-06-10; 4.5 log retention still 0 — needs log sink, partner/ops) — ⚠️ **3 HIGH-severity zeros (10.2, 10.4, 10.6)**

---

## Scorecard — 2026-06-10 (evening rescore — code-item sweep)

| Dimension | Raw | Weighted | Max | HIGH zeros |
|-----------|-----|----------|-----|------------|
| 1. Legal | 12 / 16 | 36 | 48 | — |
| 2. Security | 16 / 16 | 48 | 48 | — |
| 3. Billing | 16 / 16 | 48 | 48 | — |
| 4. Observability | 7 / 12 | 14 | 24 | — |
| 5. Load | 10 / 10 | 20 | 20 | — |
| 6. Data integrity | 9 / 10 | 18 | 20 | — |
| 7. Support | 7 / 10 | 7 | 10 | — |
| 8. Brand | 7 / 10 | 7 | 10 | — |
| 9. Sales | 7 / 10 | 7 | 10 | — |
| 10. Risk | 8 / 12 | 16 | 24 | **10.6** |
| **TOTAL** | — | **221** | **262** | **1 HIGH zero (10.6)** |

**Score:** 221 / 262 = **84.4%**

## Verdict — 2026-06-10 (evening)

🟡 **221/262 clears the 210 paid-launch number. The ONLY remaining blocker —
for soft launch AND paid launch — is the HIGH-severity zero on 10.6
(insurance quote), a partner phone call.** The moment a quote is in hand,
both gates open by this rubric's own decision rules.

Code-item sweep closed this cycle (2026-06-10 evening): 2.7 Semgrep triage
(41 findings — 3 real, all fixed), 3.8 invoice reconciliation service + eval,
4.4 MRR/churn admin dashboard, 5.2 DB pool audit + prod burst test, 7.4
stale-note correction (churn capture already shipped), 9.3 pricing page A/B
(migration 134), 9.4 referral attribution end-to-end. Dimensions 2 (Security),
3 (Billing), and 5 (Load) are now complete.

Latent bugs fixed during the sweep: admin analytics rate limits never
enforced (decorator order), global 422 handler returned 500 on any
field_validator ValueError (ctx not JSON-serializable), three wrong inline
plan-price maps in admin analytics.

Everything still below 2 is partner/account-shaped: 1.5/1.6/1.8 (entity,
merchant agreement, DPA counsel), 4.1/4.2/4.3/4.5 (Railway token, Sentry
OAuth, uptime service, log sink), 6.1 (restore drill), 7.2/7.5 (support SLA,
status page), 8.3/8.5 (tagline sign-off, case study), 9.2/9.5 (email DNS,
outreach templates), 10.4/10.5 rehearsals, 10.6 insurance.

Prior: 208 (2026-06-10 morning), 191, 173, 157 (2026-04-25 NO-GO).

## Highest-leverage next moves (ordered by leverage per hour)

1. **10.6 insurance quote** — the single gate on everything. Partner call, ~1 hour.
2. **4.5 log retention (0) + 4.3 uptime service** — account setup (log sink, UptimeRobot), then small wiring. Dim 4 is the weakest engineering dimension left.
3. **7.5 status page (0)** — hosted status product, an afternoon.
4. **6.1 restore drill** — run one Supabase PITR restore into a scratch project, document it. Half a day, closes Dim 6.
5. **8.5 case study** — MTOptions writeup once they've tested. Closes the last Brand point with real evidence.

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

**Current state: NO-GO — solely on the 10.6 HIGH zero (insurance quote). Score 221 ≥ 210; the call flips this straight to GO.**

## Cadence

Rescore monthly while pre-launch. After launch, rescore quarterly + on any HIGH-severity incident.

## Who scores what

- Dimensions 1, 3, 7, 8, 9 → partners (non-engineer tasks)
- Dimensions 2, 4, 5, 6 → engineer (Aidan)
- Dimension 10 → partners + engineer jointly

## Artifacts required when scoring 2

Each 2-score needs a linked artifact — test run, PR, URL, doc. "I think we did this" does not count.
