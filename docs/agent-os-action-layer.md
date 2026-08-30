# Agent OS action layer

How an agent does something, rather than drafting something.

```
owner ask
  → orchestrator            (agent-service/src/agent-os/agents/_orchestrator.ts)
  → department agent        (agents/departments.ts)
  → tool selection          (a department's resolveAction hook)
  → executeAction()         (actions/executor.ts)  ← the only entry point
      ├─ resolve the tool   (actions/registry.ts)
      ├─ validate input     (the tool's Zod schema)
      ├─ evaluate policy    (actions/policy.ts)
      ├─ create the record  (actions/store.ts)
      ├─ stop here if approval is required
      ├─ execute            (the tool's execute(), through its ports)
      ├─ verify             (the tool's verify(), an independent read-back)
      └─ persist the outcome
  → structured result back to the agent
  → audit row in os_tool_executions        (backend/services/os_tool_executions.py)
```

The rule the whole layer exists to enforce: **agents never call `tool.execute()`.**
They call `executeAction()`, which is the only place policy, approval,
verification and audit can be applied. Anything that bypasses the executor
bypasses the security model.

## Where the code lives

| Concern | File |
|---|---|
| Types, risk levels, lifecycle | `agent-service/src/agent-os/actions/types.ts` |
| Tool definition + validation | `actions/define-tool.ts` |
| Registry | `actions/registry.ts` |
| Risk / approval policy | `actions/policy.ts` |
| Persistence seam | `actions/store.ts` |
| Capability ports | `actions/ports.ts` |
| Executor | `actions/executor.ts` |
| Reference tools | `actions/tools/` |
| Redaction before persistence | `actions/sanitize.ts` |
| Request-scoped store/ports (agent-service) | `src/agent-os-runtime/action-collector.ts`, `scoped-providers.ts` |
| Approval execution entry point | `src/agent-os-runtime/approve-action.ts`, `POST /actions/approve` |
| Persistence + approval API (data plane) | `backend/services/os_tool_executions.py`, `backend/routers/os_tool_executions.py` |
| Claim-gated runner (injected port only) | `backend/services/os_tools.py` |
| Table | `migrations/195_os_tool_executions.sql` + `196_os_tool_executions_status_no_approved.sql` |

## Risk levels

| Level | Meaning | Examples | Default |
|---|---|---|---|
| 0 | Read-only | fetch records, inspect availability, search | runs |
| 1 | Reversible internal mutation | internal note, internal CRM field | runs |
| 2 | External communication | email, SMS, published social post | needs approval |
| 3 | Financial, legal, destructive | refund, charge, delete, payroll, binding agreement | always needs approval |

A tenant may **tighten** this (`approvalThreshold`, `disabledToolIds`,
`alwaysApproveToolIds`) and may never loosen it: level 3 always requires
approval, and a tenant cannot drop an approval a tool declared for itself.
`defineTool` refuses a definition that breaks the model — a level-0 tool that
mutates, or a level-2 tool that does not declare `requiresApproval`, fails at
import time and therefore in CI.

## Lifecycle

Two axes. Do not merge them.

**`status`** is parked / running / terminal only:

`pending_approval` | `running` | `succeeded` | `failed` | `verification_failed` | `denied` | `cancelled`

**`approval_state`** is `not_required` | `pending` | `approved` | `rejected`.

`approved` is **not** a status. The approvals queue keys off
`status='pending_approval'` and/or `approval_state='pending'`.

```
pending_approval ──approve──▶ running ──▶ succeeded
       │                         ├──▶ failed
       │                         └──▶ verification_failed
       ├──reject──▶ denied
       └──policy denial──▶ denied
(policy allows) ──▶ running ──▶ …
```

On approve, `status` moves `pending_approval → running` and `approval_state`
moves `pending → approved`. Policy-allowed actions are created as `running`
with `approval_state=not_required`.

`status` and `verification_state` are also separate: "it ran" and
"we confirmed it landed" must never be conflated. A tool that runs but fails its
verifier ends `verification_failed` and returns no output to the agent — it is
never reported as success.

Exactly-once is enforced with conditional transitions, not read-then-write:

- the data plane moves a row out of `pending_approval` to `running` with a
  conditional `UPDATE ... WHERE status = 'pending_approval'` before it calls the
  engine, so a double-clicked approval never reaches the engine twice;
- inside the engine, `store.transition()` only succeeds from an expected status,
  so concurrent callers inside one request collapse to one invocation.

If the engine does not answer an approval, the row stays `running` with
`error.code = "engine_unavailable"`. The outcome is genuinely unknown, and no
automatic retry is attempted — that is the only choice that cannot double a
real-world side effect.

## Adding a tool

1. Create `actions/tools/<tool_id>.ts` and define it with `defineTool`:

```ts
export const sendQuoteEmail = defineTool({
  id: "send_quote_email",            // snake_case, stable, persisted
  displayName: "Send quote email",
  description: "Emails a prepared quote to a customer.",
  department: "sales",               // an agent_id from the agent registry
  requiredConnectors: ["gmail"],     // for per-tenant availability gating
  riskLevel: 2,                      // external communication
  mutating: true,
  requiresApproval: true,            // level >= 2 must declare this
  inputSchema: z.object({ customer_id: z.string(), body: z.string().min(1) }),
  outputSchema: z.object({ messageId: z.string() }),
  async execute({ input, context }) {
    const sent = await context.ports.email.send({ ... });   // never a raw client
    context.declareEffect({ port: context.ports.email.name, durable: true });
    return { messageId: sent.id };
  },
  async verify({ output, context }) {
    const found = await context.ports.email.get(output.messageId);
    return { verified: Boolean(found), detail: found ? "message confirmed sent" : "not found" };
  },
});
```

2. Register it in `actions/registry.ts` (duplicate ids throw).
3. If it needs a capability the ports do not have yet, add a port to
   `actions/ports.ts` and implement it in the host — a tool never opens a
   database handle, an HTTP client or a credential store itself.
4. Add tests. `actions/_testkit.ts` gives you a fresh store, ports and registry.

**Do not register a tool whose integration does not exist yet.** The registry is
the list of things the product can actually do; test-only doubles live in
`_testkit.ts`.

## How an agent invokes a tool

A department declares a `resolveAction` hook. It returns a tool request when the
ask is clearly an action, and `undefined` to fall through to normal drafting —
a half-understood ask must never become a silent write. See
`agents/admin_records_actions.ts` for the shipped example, and
`agents/_department.ts::maybeRunAction` for how the outcome becomes the owner's
answer.

The agent gets a structured outcome (`succeeded`, `pending_approval`, `denied`,
`failed`, `verification_failed`) and reports it honestly; tool use also shows up
in the reasoning trace as `tool_select`, `tool_policy`, `tool_execute` and
`tool_verify` steps.

## Where execution records are stored

`os_tool_executions`, one row per attempt, tenant-scoped by `client_id`
(migration 195). The engine returns the records it created in the `/orchestrate`
response bundle (`record.toolExecutions`) and
`agent_os_bridge.persist_orchestration` writes them. Read them through:

- `GET /api/v1/os/tool-executions?status=pending_approval` — the queue
- `GET /api/v1/os/tool-executions/{id}` — one execution
- `POST /api/v1/os/tool-executions/{id}/approve` — owner-only, runs it once
- `POST /api/v1/os/tool-executions/{id}/reject` — owner-only

Inputs and results are sanitized before they leave the engine: keys that look
like credentials are redacted and oversized payloads truncated
(`actions/sanitize.ts`). Never widen that.

This is **not** `os_action_runs` (migration 126). That table records the channel
handler fired when an owner approves a *deliverable* ("send this drafted SMS")
and is unchanged. This one records an agent's own *tool* choice mid-run.
The two tables stay dual — they are not merged.

**L2 audit fail-closed.** Risk level 2+ (external communication / high impact)
cannot be queued or treated as sent if the `os_tool_executions` row cannot be
written. L0/L1 persist stays best-effort so a note-audit blip does not break
the owner's turn.

## Leftovers for Slice B (do not sneak Gmail into A)

- L2 idempotency is required on persist (migration 197). List/get redact
  `input` for non-owners.
- Data-plane B-blockers are in production without a live send: unknown
  timeout/lost-response stays non-terminal (`apply_unknown_send_outcome`);
  a later re-drive rfc822msgid-adopts via `_run_data_plane_tool` and an
  injected mailbox port; Python email validation runs *before* the approval
  claim; `os_tools.run_tool` is unreachable without that claim.
- `send_email` is Sales-only (`department: "sales"`) and gated by
  `SEND_EMAIL_ENABLED` (default off). Flag-off refuses propose/queue/execute
  — no Gmail `send_message` and no outbound mail. Production execute uses
  `gmail_connector.send_message` + `find_message_id_by_rfc822_msgid` through
  the existing claim path. No `communication_actions`, no 5-department
  proposal wiring, no routing change. Dual `os_actions` vs
  `os_tool_executions` stays documented, not merged. Migrations 195/196/197
  are untouched.

## Verification

`verify()` is an independent read-back, not a restatement of what `execute()`
returned: `add_customer_note` re-reads the customer's notes and confirms the note
it wrote is there. The data plane verifies again when it applies the write for
real — a note that cannot be applied to the customer's record downgrades its
execution row to `verification_failed`, so the history never claims a write that
is not there.

A tool with no verifier records `not_applicable`. That is honest, and it is
never presented as "verified".

## What plugs in next

The Tool interface is the seam future capabilities implement, without the
executor, policy, registry or audit trail changing:

- **Gmail / Outlook, Google / Microsoft Calendar, CRM, invoicing** — new ports
  plus level-2/3 tools; the approval gate already blocks them until an owner says
  yes.
- **MCP tools** — one adapter that turns an MCP tool descriptor into a
  `ToolDefinition` (its JSON Schema becomes the Zod input schema, its risk level
  is declared by us, not by the server).
- **Browser automation / computer use** — a driver port and tools that call it.
  The rest of the system does not care whether an action happened through an API
  or a GUI, because both arrive as the same `ToolDefinition`.

## Tests

| What | Where |
|---|---|
| Registry, policy, executor, approval, idempotency, audit | `agent-service/src/agent-os/actions/executor.test.ts` |
| Reference tools + sanitizer | `agent-service/src/agent-os/actions/tools.test.ts` |
| Agent → tool → executor → verification, end to end | `agent-service/src/agent-os/actions/agent-integration.test.ts` |
| Request scoping, tenant isolation, approval round trip | `agent-service/src/agent-os-runtime/action-runtime.test.ts` |
| Persistence, note application, approval API | `backend/tests/test_os_tool_executions.py` |
| Unknown send, email-claim parity, unclaimed run_tool | `backend/tests/test_gmail_send_message.py` |
| Sales-only send_email flag (default off, no live send) | `backend/tests/test_send_email_flag.py` + `agent-service/src/agent-os/actions/send_email.test.ts` |

Run them with `cd agent-service && npm run typecheck && npm test`, and
`python -m pytest backend/tests/test_os_tool_executions.py`. Both run in CI
(`.github/workflows/pr-check.yml`) and in `scripts/ci_local.sh`.
