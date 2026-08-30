# Milestone 6 — Controlled Gmail send proof

**Status:** PREPARED — blocked on explicit owner authorization  
**Blockers:** `SEND_EMAIL_ENABLED` must remain default OFF in production; real send requires Aidan approval.

## Preconditions (test tenant only)

| Item | Requirement |
|------|-------------|
| Tenant | Non-production test tenant (`client_id` in staging) |
| Gmail | Connector connected for that tenant only |
| Recipient | Address you control (e.g. `smoke+<date>@yourdomain.com`) |
| Flag | `SEND_EMAIL_ENABLED=1` in **staging agent-service only** — never production |
| Data | No production customer data in ask or body |

## Expected state transitions

```
Owner ask (email + address in ask)
  → Sales department, send_email proposal
  → os_tool_executions: status=pending_approval, approval_state=pending
  → Gmail: untouched
Owner approves → claim → run_tool(send_email)
  → Gmail: exactly one message, Message-ID <aos-{execution_id}@actions.agentnexlify>
  → os_tool_executions: status=succeeded, verification_status=verified
Replay approve / redrive
  → No duplicate send (idempotency + RFC822 Msg-ID search)
```

## Automated prep (no send)

These run in CI today without credentials:

```bash
python3 -m pytest backend/tests/test_send_email_flag.py backend/tests/test_gmail_send_message.py -q
cd agent-service && npm test -- src/agent-os/actions/send_email.test.ts
```

## Manual proof (owner authorization required)

Follow `docs/agent-action-eval.md` § Manual live-Gmail smoke procedure (steps 1–10).

**Ask template:**

> Email smoke-test+20260830@example.com with subject "AOS smoke 2026-08-30" and body "Milestone 6 controlled send — safe to delete."

**Verify after approval:**

1. `os_tool_executions` row: `tool_id=send_email`, `agent_id=sales`, `requires_approval=true`
2. Gmail message headers: `Message-ID` matches deterministic fingerprint
3. Recipient and subject match approval card
4. Second approve on same `execution_id` → no duplicate in Gmail

## What was NOT done in this milestone

- `SEND_EMAIL_ENABLED` was **not** set in any production environment
- No live Gmail send was executed from the cloud agent VM (no staging credentials)
- Non-Sales departments may **propose** `send_email` (communication capability) but policy denies execution unless `agent_id=sales` and flag is on
