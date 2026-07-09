# Session Summary — 2026-06-23 — Cold-Outreach Launch Prep + Plan-Gating / Webhook Fixes

## Overview
Two parallel tracks this session: (1) standing up the cold-email outreach motion end-to-end,
and (2) a full "test every feature, fix what's broken" pass that uncovered and fixed a cluster
of bugs introduced by the 2026-06-15 two-plan repricing, plus a webhook event-loss bug.

All engineering changes shipped to `main` via fast-forward from
`claude/local-ci-workaround-ukkysg`. Full suite went 2156→2172 passing (0 failed).

## Engineering — what shipped

| Commit | What |
|--------|------|
| `b3279b07` | Fixed 7 failing tests — stale MRR plan names + a widget-test patch-leak |
| `57f2bb4d` | Plan-gating for repriced plans (chatbot/agent_os) — addresses #292 + #293 issue 1 |
| `29ed1d43` | Reconciliation new-plan caps (#293 issue 2) + refreshed stale CLAUDE.md plan section |
| `3a958e5f` | #308 — release idempotency row on webhook handler failure |
| `354cdb14` | (pre-goal) CAN-SPAM compliance footer on cold sequences |

### Root causes (full detail in bug-patterns.md)
- **Repricing half-migration (#292/#293):** the 2026-06-15 reprice to `chatbot` ($19.99) /
  `agent_os` ($99.99) updated billing (`stripe_service.py`, `ai_usage_guard`) but left 6 feature
  gates hard-coding the retired plan names (`growth`/`autopilot`/`professional`/`enterprise`).
  Result: paying `agent_os` customers were locked out of every premium feature (Zapier, unlimited
  SMS, document drafting, lead qualification, branded automation, white-label). Fixed by adding
  `agent_os` to all premium gates; `chatbot` stays widget/chat-only per documented intent.
- **MRR test staleness:** test asserted on retired plan names; product (plan-agnostic endpoint)
  was correct. Updated test to real plans (Rule 10 — contract changed, evidence cited).
- **Widget patch-leak:** `tests/test_widget_api.py` patched the same target twice; teardown
  stopped patchers in forward order, leaving `widget_chat_helpers.get_service_supabase`
  permanently mocked and bleeding into later tests. Removed the duplicate patch.
- **Webhook event loss (#308):** idempotency row written before the handler ran; on handler
  exception the NULL-response row persisted, every Stripe retry short-circuited as an in-flight
  duplicate, and the event was dropped (dunning-locked tenants stuck). Added
  `idempotency.delete_key()` + release-on-failure in both webhook endpoints.

### Docs
- `CLAUDE.md` "Plan names + prices" rewritten from the retired tiers to the live two-plan model
  (chatbot / agent_os), with the gating split documented and old names demoted to legacy.

### Open decision (not assumed)
- `chatbot`-tier feature policy: mapped as widget/chat-only (no premium back-office gates). If
  product wants chatbot to include SMS / Zapier / lead-qual, each is a one-line flip + a matching
  assertion in `backend/tests/test_plan_gating_new_plans.py`. #292/#293 left open for that call.
- New-plan agent-run caps in `billing_reconciliation.py` left at default (two-plan run-cap policy
  is a product TBD per #293).

## Cold-outreach motion — current state

### Lead engine
- `scripts/leadgen/` produced **381 deduped leads** (roofing 220 + HVAC 161) across CT/RI/MA/NY
  via Google Places, enriched with email + owner name + contact-form URL.
- Filtered to **218 "personal" emails** (dropped 163 role inboxes: info@, service@, sales@, etc.).
  Delivered as xlsx (clean + filtered-out sheets) and a filtered csv.

### Instantly (app.instantly.ai)
- **9 inboxes** (aidan / niko / louis × agentnexlifyhq.com, getagentnexlify.com, tryagentnexlify.com),
  AirMail/DFY, all warming. Launch gate: warmup completes **~July 10**.
- Campaign **"Roofing CT/NE"** built, **paused**. Email = Niko's "competitors are using AI" copy,
  greeting "Hi," (list has no first names), link = homepage `https://www.agentnexlify.com/`.
- Deliverability config recommended: unsubscribe-link header ON, text-only ON, open/link tracking
  OFF, provider matching ON, stop-on-auto-reply ON, BounceProtect ON (no risky emails).
- Schedule: America/New_York, Mon–Fri (or Tue–Thu), 8 AM–4 PM.

### Launch checklist (when warmup done)
1. Lower daily limit to ~50–90/day (ramp ~20%/wk to the 270 nine-inbox ceiling).
2. Confirm CAN-SPAM physical address in the email body (still the open gap).
3. Run email verification on the 218.
4. Unpause = launch. Watch bounce (<3–4%) + spam complaints for 48h.

### Still open / operator to-do
- CAN-SPAM physical mailing address not yet in the campaign body.
- Decide single mixed campaign vs split roofing/HVAC (split recommended for cleaner tracking).
- HVAC campaign not built yet; if it shares the 9 inboxes, daily limits are a combined ceiling.

## Verification
- `scripts/ci-local.sh` — ALL GATES PASSED after each engineering commit.
- Full suite: 2172 passed, 36 skipped, 0 failed. Frontend vitest: 140 passed.
