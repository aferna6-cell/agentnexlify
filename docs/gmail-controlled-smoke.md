# Controlled Gmail proof (Milestone 6, workstream E)

Prepared. **Blocked on Aidan's explicit approval** to enable `SEND_EMAIL_ENABLED`
on a test tenant and to send one real message.

## Preconditions (none of these are production)

- Test tenant (not a customer `client_id`)
- Test Gmail account connected through the existing OAuth vault
- Known harmless recipient (owner-controlled inbox)
- Owner claim required — no auto-approve
- `SEND_EMAIL_ENABLED` remains **off** in Railway / production / `.env.example`

## Expected state machine

1. Owner ask with a written recipient address → Sales proposes `send_email`
   (only if the flag is on **and** the department is Sales).
2. Row parks: `status=pending_approval`, `approval_state=pending`.
3. Gmail is untouched (`sent` count 0) before claim.
4. Owner `POST /tool-executions/{id}/approve` claims the row:
   `status=running`, `approval_state=approved`, `approved_by` set.
5. Data plane sends exactly once via `gmail_connector.send_message`.
6. Message is locatable by deterministic `Message-ID` / `rfc822msgid:`.
7. Recipient and subject verify against the approved input.
8. Row reaches `succeeded` (or `verification_failed` if read-back fails) with
   the approval axis still `approved`.
9. Replay / re-approve / redrive rfc822msgid-adopts — no second send.

## What is already proven without a live send

- Flag default off: `backend/tests/test_send_email_flag.py`
- Claim-before-execute, unknown-send adopt, unclaimed `run_tool`:
  `backend/tests/test_gmail_send_message.py`, `test_os_tool_executions.py`
- Engine never sends: `send_email.execute()` throws `data_plane_only`
- Eval FakeGmailPort: `evals/safety-gate.test.ts` D7 + send boundary abort

## Approval boundary

Do **not** set `SEND_EMAIL_ENABLED=1` in production.

To run the live smoke, Aidan must:

1. Confirm the test tenant id and test Gmail.
2. Confirm the harmless recipient.
3. Explicitly authorize flipping the flag **only** on that test environment.
4. Authorize exactly one send.

Until then: **no real send has occurred**.
