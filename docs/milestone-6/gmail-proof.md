# Milestone 6 — controlled Gmail proof

## What is proven in CI

`backend/tests/test_controlled_gmail_smoke.py` walks the production data-plane
contract on `FakeGmailPort`:

1. A Sales `send_email` proposal parks in `pending_approval`.
2. Gmail is untouched before the owner claim.
3. Claim records `approval_state=approved` and moves status to `running`.
4. Exactly one message is sent.
5. The sent message is locatable by the deterministic rfc822 Message-ID.
6. Recipient and subject match the proposal.
7. The execution row reaches a terminal succeeded state.
8. Replay/redrive cannot create a duplicate send.
9. A different tenant cannot claim the row.

`SEND_EMAIL_ENABLED` remains default OFF.

## Live send — approval boundary

A real send requires Aidan's explicit approval of all of:

- a test tenant (not a production customer)
- a test Gmail account
- a known harmless recipient
- `SEND_EMAIL_ENABLED=1` in that environment only

**No production environment flag was changed.** The live send did not run.
