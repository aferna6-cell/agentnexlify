# Spec: Weekly Value Digest

**Status:** Draft (2026-06-22)
**Author:** Aidan (via Claude)
**Gap:** G2 — highest open product gap per `planning/gap-analysis-small-business-2026-06-10.md`
**Target tier:** all paying tenants (`chatbot` + `agent_os` + grandfathered paid)

## 1. Problem
Small-business owners cancel when they can't *see* the value. AgentNexLiFy captures leads, books
appointments, and answers visitors, but the owner never gets a plain "here's what your AI did for
you, in dollars" summary. The digest is the cheapest retention lever — it makes invisible work
visible on a weekly cadence.

## 2. Goals
- Email each paying tenant a **weekly** rollup of what their AI front desk did, framed in dollars.
- Pull only from existing data (no new capture): leads, conversations, appointments, invoices.
- **Draft-then-send**: never auto-send the first run; gate behind owner opt-in + a preview.
- Reuse existing infra: Resend (`email_sender`), `email_sequences`/templates patterns, the
  scheduled-jobs runner.

## 3. Non-Goals (V1)
- Per-channel marketing analytics (that's the marketing surface).
- Configurable cadence/segmentation (V1 = weekly, all paying tenants).
- SMS digest (email only V1).
- Benchmarking against other tenants.

## 4. Metrics in the digest (all source-backed, existing tables)
| Metric | Source |
|---|---|
| New leads captured (count + Δ vs prior week) | `leads` (by `client_id`, `created_at`) |
| Conversations handled | `conversations` / `chat_messages` |
| Appointments booked | `appointments` |
| Estimated value | `invoices` issued/paid this week, or leads × tenant avg job value |
| After-hours captures | leads/conversations outside `business_hours` |
| Top question themes (agent_os only) | `conversations.intent` (migration 154) |

"Estimated value" must be clearly labeled an estimate; never invent a number — if no invoice/
avg-value data, show counts only and omit the dollar line.

## 5. Design
- **Job:** new module `backend/services/automation/weekly_value_digest.py` (own file, Rule 12).
  Computes the per-tenant rollup deterministically (SQL aggregates, no LLM). Scheduled weekly via
  the existing scheduled-jobs runner (mirror `conversation_insights` monthly job).
- **Template:** Resend HTML template, owner-voice, dollar-framed, one screen, CTA to dashboard.
  CAN-SPAM unsubscribe footer (reuse existing footer helper).
- **Send gate (critical):** a `weekly_digest_opt_in` tenant flag (default off). First run for any
  tenant produces a **preview/draft** surfaced to the owner (or to the founder for QA) — actual
  send only after opt-in. No bulk send without explicit enablement.
- **Idempotency:** one row per (tenant, week) in a `digest_sends` ledger; re-runs no-op (reuse
  the idempotency pattern, GH #308 lesson).

## 6. Edge cases
- Tenant with 0 activity this week → send an encouraging "quiet week" variant OR skip (decide at
  build; default skip to avoid annoyance).
- New tenant <7 days old → skip until a full week of data.
- Missing avg-value data → omit dollar line, keep counts.
- Multi-worker: compute in the scheduled job only (single runner), not per request.

## 7. Acceptance criteria
- Deterministic rollup unit-tested against seeded data (happy path + zero-activity + new-tenant).
- No send occurs without `weekly_digest_opt_in = true`.
- Idempotent: running the job twice for the same week sends at most once.
- Dollar figures never fabricated; estimate clearly labeled.
- CAN-SPAM unsubscribe present.

## 8. Open questions (need owner decision)
1. Zero-activity week: skip or send "quiet week" nudge?
2. "Estimated value" basis: paid invoices only, or leads × a tenant-set average job value?
3. Send day/time (default: Monday 8am tenant-local)?
4. First rollout: opt-in only, or auto-enable for the top beta tenants (e.g. MTOptions) after QA?

## 9. Rollout
Build behind the opt-in flag → QA on the founder account + MTOptions → enable per tenant. Its own
PR; follows `WRITE-PRD → GRILL-ME → TDD → build`.
