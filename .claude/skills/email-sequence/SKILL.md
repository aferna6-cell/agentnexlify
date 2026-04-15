---
name: email-sequence
description: Design multi-email campaigns (onboarding, nurture, re-engagement, upsell). Load when editing backend/routers/marketing_campaigns.py, backend/routers/sequences.py, or authoring tenant email flows via Resend integration.
origin: coreyhaines31/marketingskills (adapted)
version: 1.0.0
triggers:
  - email sequence
  - drip campaign
  - onboarding emails
  - nurture sequence
  - re-engagement flow
  - upsell campaign
---

# Email Sequence — Multi-Email Campaign Design

Multi-email campaign design for AgentNexLiFy marketing addon. Uses Resend via `backend/services/resend_service.py` (or equivalent).

## When to Use
- Editing `backend/routers/marketing_campaigns.py` or `backend/routers/sequences.py`
- Authoring tenant-facing email flows via Resend
- Designing onboarding/nurture/re-engagement/upsell sequences
- Planning cadence + branching logic for campaigns

## When NOT to Use
- Single transactional emails (use Resend directly)
- In-app notifications (different channel entirely)
- Churn-specific retention emails (use `churn-prevention` first for offer design)

## Five sequence archetypes

1. **Onboarding (days 0-14)** — welcome, widget install, first conversation, first lead, first appointment, upgrade prompt. Goal: first-value in <72hr.
2. **Nurture (weekly, indefinite)** — industry tips, case studies, feature announcements. Low-pressure. Goal: stay top-of-mind until buying signal.
3. **Re-engagement (triggered: 30d inactive)** — "we miss you", new feature highlight, cancel survey trigger. Goal: reactivate or learn why they churned.
4. **Upsell (triggered: usage threshold)** — "you hit X conversations this month, upgrade to unlock Y". Time it to usage spikes. Goal: plan upgrade.
5. **Trial-to-paid (days 0-7 of trial)** — daily value email. Strongest conversion on day 3-5 when they've tasted value.

## Sequence design checklist
- Subject line <50 chars, personalized with tenant name or first name
- One CTA per email (don't split attention)
- Plain text fallback (deliverability)
- Unsubscribe link (CAN-SPAM + GDPR required)
- `{{ tenant.name }}`, `{{ user.first_name }}` template vars resolved server-side
- A/B test subject lines via `backend/routers/ab_tests.py`

## Timing playbook (CST, tenant timezone aware)
- Day 0 (signup): immediate + 4hr follow-up
- Day 1-3: daily
- Day 4-7: every 48hr
- Day 8-14: every 3-4 days
- Week 2+: weekly max
- Never: weekends for B2B, before 9am or after 6pm local

## AgentNexLiFy-specific hooks
- Sequences stored in `sequences` table (see schema-log)
- Triggered by events in `events` table or cron scans in `backend/routers/automation_rules.py`
- Resend webhook `email.delivered` / `email.opened` / `email.clicked` → update `sequence_runs.status`
- Unsubscribe updates `leads.email_opted_out = true` — respect on all future sends

## Metrics per sequence
- Delivery rate (>95% healthy)
- Open rate (>25% B2B, >35% onboarding)
- Click rate (>3% nurture, >8% onboarding)
- Unsubscribe rate (<0.5% per send)
- Conversion rate (sequence-specific goal — upgrade, appointment, reply)

## Anti-patterns
- Don't hard-send 3 emails in one day (spam filter instant flag)
- Don't resend same email if open tracked (Resend handles dedupe)
- Don't embed large images (deliverability)
- Don't use "Re:" or "Fwd:" fake prefixes (CAN-SPAM violation)

## Full upstream reference
coreyhaines31/marketingskills — email-sequence SKILL. Install:
```
npx skillsadd coreyhaines31/marketingskills
```
