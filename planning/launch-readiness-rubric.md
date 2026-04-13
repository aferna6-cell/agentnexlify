# AgentNexLiFy — Launch Readiness Rubric

**Purpose:** Decide go / no-go for paid launch via evidence, not gut. Partners + engineer run this together. Rescore monthly until shipped.

**How to score:** Each criterion 0 / 1 / 2. Multiply by weight. Sum per dimension. Sum dimensions. Compare vs threshold.

- **0** — not done, or known broken
- **1** — partial, works for happy path, gaps exist
- **2** — done, tested, documented

**Go threshold:** ≥ 160 / 200 (80%) AND zero criterion scoring 0 in a HIGH-severity dimension.

---

## Dimension 1 — Legal & compliance (weight: 3)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Terms of service drafted + linked in signup | | |
| 1.2 | Privacy policy drafted + covers tenant data + PII + AI | | |
| 1.3 | GDPR / CCPA data deletion endpoint works | | |
| 1.4 | Cookie/consent banner present where required | | |
| 1.5 | Business entity registered (LLC / C-corp) + bank + EIN | | |
| 1.6 | Merchant agreement signed (Stripe Connect or direct) | | |
| 1.7 | Written AI-disclosure in widget greeting ("powered by AI") | | |
| 1.8 | DPAs available for customers who ask | | |

**Subtotal:** ___ / 16 × 3 = ___ / 48

---

## Dimension 2 — Security (weight: 3, HIGH severity)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 2.1 | Multi-tenant isolation verified (RLS on every table OR tenant_id filter on every query) | | |
| 2.2 | SSRF blocked on all outbound HTTP (webhooks, crawler, onboarding) | | ✓ 2026-04-13 |
| 2.3 | Webhook signature verification on inbound (Stripe, Twilio, Resend) | | |
| 2.4 | All secrets in env vars, zero in git history | | |
| 2.5 | Auth rate-limited on /login, /signup, /reset | | |
| 2.6 | JWT rotation + refresh flow tested | | |
| 2.7 | Pen test OR automated security scan run (semgrep, snyk) | | |
| 2.8 | Incident response playbook written (who, what, in what order) | | |

**Subtotal:** ___ / 16 × 3 = ___ / 48

---

## Dimension 3 — Billing & revenue integrity (weight: 3, HIGH severity)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 3.1 | Stripe webhook idempotency tested (replay same event twice) | | |
| 3.2 | Failed-payment dunning flow tested end-to-end | | |
| 3.3 | Proration on upgrade / downgrade tested | | |
| 3.4 | Cancellation preserves access until period end | | |
| 3.5 | Usage metering matches Stripe meter events ±1% | | |
| 3.6 | Refund flow tested (partial + full) | | |
| 3.7 | Trial → paid transition tested across all plans | | |
| 3.8 | Invoice generation reconciles against Stripe dashboard | | |

**Subtotal:** ___ / 16 × 3 = ___ / 48

---

## Dimension 4 — Observability (weight: 2)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 4.1 | Error alerts fire within 5 min of prod error (Slack / email) | | Railway → Slack wired, needs RAILWAY_TOKEN |
| 4.2 | Sentry or equivalent captures unhandled exceptions | | OAuth pending |
| 4.3 | Uptime monitor (external) with SLO ≥ 99.5% | | |
| 4.4 | Key business metrics on a dashboard (signups, MRR, churn, activation) | | |
| 4.5 | Log retention ≥ 30 days | | |
| 4.6 | Database advisor warnings all resolved | | Zero as of 2026-04-09 |

**Subtotal:** ___ / 12 × 2 = ___ / 24

---

## Dimension 5 — Load & capacity (weight: 2)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 5.1 | Load test run at 10× expected concurrent (p95 < 1s) | | |
| 5.2 | Database connection pool sized + tested | | |
| 5.3 | Claude API rate limits understood + surfaced to user | | |
| 5.4 | Widget render verified on slow 3G (Lighthouse PWA test) | | Chrome install pending |
| 5.5 | Runaway-cost kill switch (per-tenant usage cap) | | |

**Subtotal:** ___ / 10 × 2 = ___ / 20

---

## Dimension 6 — Data integrity (weight: 2)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 6.1 | Daily automated backup verified restorable | | |
| 6.2 | Schema migrations numbered + forward-only | | ✓ 100 applied |
| 6.3 | Pre-commit blocks dropped-column queries | | ✓ CHECK 8 added |
| 6.4 | Integration tests cover critical tables | | ✓ regression guards added |
| 6.5 | PII minimization — no unnecessary customer data stored | | |

**Subtotal:** ___ / 10 × 2 = ___ / 20

---

## Dimension 7 — Support & onboarding (weight: 1)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 7.1 | Help docs / knowledge base accessible to customers | | |
| 7.2 | Support email monitored within 24h | | |
| 7.3 | Onboarding wizard completes without manual intervention | | |
| 7.4 | Cancel-flow is self-serve (no email required) | | |
| 7.5 | Status page exists | | |

**Subtotal:** ___ / 10 × 1 = ___ / 10

---

## Dimension 8 — Brand & positioning (weight: 1)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 8.1 | Landing page states price + plan + ICP clearly | | |
| 8.2 | Demo widget embedded on landing works | | |
| 8.3 | Tagline / elevator pitch agreed by all partners | | |
| 8.4 | Competitor FAQ (vs GoHighLevel, Drillbit, Podium) | | |
| 8.5 | Case study or design-partner logo visible | | |

**Subtotal:** ___ / 10 × 1 = ___ / 10

---

## Dimension 9 — Sales infrastructure (weight: 1)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 9.1 | Inbound lead capture on marketing site | | |
| 9.2 | Outbound email domain warmed + SPF/DKIM/DMARC clean | | Resend DNS pending |
| 9.3 | Pricing page A/B test wired (Growthbook / equiv) | | |
| 9.4 | Referral / affiliate tracking | | |
| 9.5 | Cold-outreach templates + partner assignment | | |

**Subtotal:** ___ / 10 × 1 = ___ / 10

---

## Dimension 10 — Risk mitigation (weight: 2, HIGH severity)

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 10.1 | Refund policy documented + honored | | |
| 10.2 | Fraud rules: velocity limits, disposable-email block, CC mismatch | | |
| 10.3 | Churn reason captured on cancel | | |
| 10.4 | Bus-factor: more than one person can deploy | | Solo — partners not engineers |
| 10.5 | Dead-man switch: if founder disappears, customers keep service for 30d | | |
| 10.6 | Insurance (E&O / cyber) quoted | | |

**Subtotal:** ___ / 12 × 2 = ___ / 24

---

## Scorecard

| Dimension | Weighted subtotal | Max | HIGH severity? |
|-----------|-------------------|-----|----------------|
| 1. Legal | ___ | 48 | no |
| 2. Security | ___ | 48 | **yes** |
| 3. Billing | ___ | 48 | **yes** |
| 4. Observability | ___ | 24 | no |
| 5. Load | ___ | 20 | no |
| 6. Data integrity | ___ | 20 | no |
| 7. Support | ___ | 10 | no |
| 8. Brand | ___ | 10 | no |
| 9. Sales | ___ | 10 | no |
| 10. Risk | ___ | 24 | **yes** |
| **TOTAL** | ___ | **262** | |

**Pass threshold:** ≥ 210 / 262 AND zero 0-scores in dimensions 2, 3, 10.

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

## Cadence

Rescore monthly while pre-launch. After launch, rescore quarterly + on any HIGH-severity incident.

## Who scores what

- Dimensions 1, 3, 7, 8, 9 → partners (non-engineer tasks)
- Dimensions 2, 4, 5, 6 → engineer (Aidan)
- Dimension 10 → partners + engineer jointly

## Artifacts required when scoring 2

Each 2-score needs a linked artifact — test run, PR, URL, doc. "I think we did this" does not count.
