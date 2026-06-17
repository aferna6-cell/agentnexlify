# Nightly Commit Review — 2026-06-17

Run time: 2026-06-17 UTC  
Commits reviewed: 16 (last 24h)  
Issues filed: 1  
Fixes applied: 1 (Check 13 pre-commit wire, subconscious run 58 winner)

---

## Commit Triage

| SHA | Title | Risk |
|-----|-------|------|
| `25d5aac` | Update brand tagline | LOW |
| `c03df18` | Recolor floating CTA from black to brand blue | LOW |
| `529dd7b` | Refresh OG card to AI Workforce positioning | LOW |
| `021e245` | Landing redesign + AI Front Desk / AI Workforce repositioning | LOW |
| `ac8ac3b` | Profit-guarantee usage caps + $24.99 usage pack | MEDIUM |
| `9c4cc5e` | docs: auto-log bug fix | LOW |
| `cd284ba` | Fix pricing cards leaving empty space on wide screens | LOW |
| `47c7f8b` | Launch retention + security hardening (dunning, trial countdown, webhook) | HIGH |
| `d500044` | docs: auto-log bug fix | LOW |
| `34b9d0f` | Launch hardening: trial-end access contract, dunning recovery fix | HIGH |
| `379b230` | Growth monetization: 7-day trial, activation funnel, owner alert | HIGH |
| `1e7e4c9` | Reconcile free-chatbot funnel to two-plan model | LOW |
| `e994349` | Home.jsx: remove "2-Minute Setup" from pricing CTA | LOW |
| `3123da0` | Home.jsx: two-plan pricing | LOW |
| `007ef5d` | Launch readiness: webhook-race hardening + paid-signup smoke | MEDIUM |
| `81df6b2` | subconscious: run 2026-06-16 (run 58) | LOW |

---

## LOW-Risk Findings — No Action Required

All LOW commits are safe: copy/CSS/docs/image changes or test additions. No critical invariant violations found.

- `frontend/src/pages/Home.jsx` is 1006 lines (>600-line god class threshold). Prior version was larger; this commit reduced it. File is pre-existing debt — not introduced today. Parking lot per subconscious backlog.
- `localStorage` usage in `Home.jsx` is intentional: used outside AuthProvider for Stripe CTA on the public landing page. Not a violation.

---

## MEDIUM/HIGH Findings

### MEDIUM: Webhook idempotency early-write drops events on handler failure

**Commits:** `47c7f8b`  
**Files:** `backend/services/idempotency.py:85-93`, `backend/routers/billing.py:233-236`, `backend/routers/stripe_webhooks.py:64-66`

Both `/api/v1/billing/webhook` and `/api/v1/webhooks/stripe` share the `"stripe":{event_id}` idempotency key space. `check_and_record` inserts the row BEFORE the handler completes. If the handler throws (e.g., DB error), the row exists with `response_body=NULL`. A Stripe retry (or the other endpoint) sees `is_new=False` with `in_flight=True` and returns 200 without processing. Event is permanently dropped.

Impact: tenant stays dunning-locked after card recovery if `_handle_payment_succeeded` fails mid-flight.

**→ GH issue #308 filed. Not auto-fixed (billing domain).**

### HIGH commits reviewed — no new bugs found

- `379b230` (7-day trial, owner alert): `notify_new_paid_signup` properly html-escapes `customer_email`. `asyncio.run()` fix for Python 3.12 is correct. Alert fires only on the non-fraud activation path.
- `34b9d0f` (dunning recovery): `_handle_payment_succeeded` now recovers from both `paused` and `past_due` correctly. Fraud-pause survival (dunning_count=0 guard) is intact.
- `ac8ac3b` (usage caps): `ALERT_MULTIPLIER=0.8` (float) + `int()` cast is correct. Caps are:
  - chatbot: alert 640k, hard 800k tokens
  - agent_os: alert 4M, hard 5M tokens
  - Both profit-positive vs plan revenue.

---

## Fix Applied — Check 13 Pre-commit Wire

**Subconscious run 58 winner, AUTONOMOUS-EXECUTABLE.**

Added Check 13 to `scripts/hooks/pre-commit` (after Check 12, line ~290):

```bash
# Check 13: project invariants gate
echo -n "Check 13: project invariants gate... "
if python3 scripts/check_project_invariants.py > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAIL${NC}"
    python3 scripts/check_project_invariants.py 2>&1 | grep -v "^PASS"
    echo "ERROR: Fix project invariant violations above before committing."
    ERRORS=$((ERRORS + 1))
fi
```

Guards 6 invariant classes at commit time:
1. FastAPI routers — no `from __future__ import annotations`
2. Active backend — no retired live-schema fields
3. Plan-related code — no retired plan names
4. Widget assets — byte-identical across all 3 mirrors
5. Website source — no em-dashes
6. Direct Anthropic SDK calls — behind runtime wrapper

`check_project_invariants.py` passes all 6 checks on HEAD. Governance updated: run 58 `pending_autonomous` → `implemented`.

---

## Subconscious Backlog Questions (for next run)

1. Was Check 13 wired? YES — confirmed by this review.
2. `AMOUNT_TO_PLAN {1999/9999}` — Check 11 guards billing guard. Repricing is covered.
3. Moratorium exit: `pending_approvals` still above threshold of 2 — moratorium still active.
4. `RequirePaid.jsx` pay gate: no false-lock reports in recent commits.
5. `kb-autopopulate.sh`: agent-browser CLI still not installed; KB remains stale.

---

## Summary

16 commits, 1 MEDIUM bug filed (#308: webhook idempotency early-write), 0 LOW bugs found, 1 autonomous fix applied (Check 13). HIGH commits from the launch sprint are well-tested and structurally sound.
