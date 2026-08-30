# Milestone 6 production status

**Status: MILESTONE 6 HOLD**

PR #705 placed the action harness, semantic pipeline, validation-v3 bakeoff,
and frozen shipped-path result on `main`. This follow-up closes review findings
that could otherwise permit untrusted inbound writes, duplicate email sends, or
false verification outcomes.

## What is production-ready after this follow-up

- Intent, business subject, channel, and authorization remain separate.
- Only authenticated owner text can authorize a mutation or email proposal.
  Inbound customer and automated text may route/draft but cannot grant authority.
- Communication proposal capability remains explicit across five departments;
  live `send_email` execution remains Sales-only and default OFF.
- Approval records preserve exact validated input, risk classification, and
  idempotency keys.
- Gmail dedup lookup failures never fall through to another send.
- Gmail success requires read-back of recipient, RFC 2047-decoded subject, and
  deterministic Message-ID.
- Inconclusive read-back stays non-terminal for operator investigation. Internal
  redrive may adopt and verify a Message-ID hit but never performs a second send.
- The safety detector has negative controls for all seven required unsafe
  classes, and crashed cases fail the CLI gate.

## Evidence

- validation-v3 routing (208): heuristic 36.5%, TF-IDF 51.9%,
  heuristic→TF-IDF 48.1%.
- frozen shipped path (215): department 80.5%, behavior 80.0%, tool 66.7%,
  approval 100%, parameter exact 70.1%, missed action 29.8%, unsafe 0/59.
- TF-IDF vs heuristic→TF-IDF is not statistically separated on validation-v3
  (paired McNemar p≈0.17), so neither is promoted.
- `SEND_EMAIL_ENABLED` remains default OFF. No production flag changed and no
  real email was sent.

## Genuine blockers

1. Haiku, heuristic→Haiku, and heuristic→TF-IDF→Haiku still need a
   credentialed validation-v3 run with explicit live-eval authorization.
2. The next scoring pass must include `acceptable_departments` and paired
   uncertainty in the recorded artifact.
3. Controlled Gmail proof requires an owner-approved test tenant, test mailbox,
   harmless recipient, and staging-only flag enablement.

The frozen benchmark already exists on main, so it is reported honestly as a
shipped-path result. It cannot substitute for the missing full candidate
selection evidence.
