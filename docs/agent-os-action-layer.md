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
| Data-plane tool bodies | `backend/services/os_tools/` |
| Redaction before persistence | `actions/sanitize.ts` |
| Request-scoped store/ports (agent-service) | `src/agent-os-runtime/action-collector.ts`, `scoped-providers.ts` |
| Approval execution entry point | `src/agent-os-runtime/approve-action.ts`, `POST /actions/approve` |
| Persistence + approval API (data plane) | `backend/services/os_tool_executions.py`, `backend/routers/os_tool_executions.py` |
| Table | `migrations/195_os_tool_executions.sql` |

## The first real external tool: `send_email`

`send_email` sends from the business's own connected Gmail. It is level 2, so
the agent may PREPARE it and only the owner can send it.

```
Sales composes the follow-up (its existing skills, unchanged)
  → the owner named a recipient address in the ask, so the composed text
    becomes a send_email proposal instead of a draft
  → executeAction() validates it and policy classifies it level 2
  → status: pending_approval, durably recorded in os_tool_executions
  → the owner sees recipient, subject, body and which agent asked
  → owner approves  →  conditional UPDATE out of pending_approval (the gate)
  → backend/services/os_tools/send_email.py sends via gmail_connector
  → the sent message is fetched back and compared
  → status: succeeded + verification: passed
```

Rejecting sets `denied`, and a later approval of a denied row does nothing —
there is no path from `denied` to a send.

### Where the body runs, and why

A tool declares `implementation: "engine"` or `"data_plane"`.

The engine holds no database handle and no OAuth tokens, by design. So a tool
that needs a tenant's credentials cannot run there. `send_email` declares
`data_plane`: the engine owns the id, the Zod input schema, the risk level and
the approval gate, and `defineTool` refuses to let a data-plane tool carry an
`execute()` at all — the engine physically cannot run it. The body lives in
`backend/services/os_tools/send_email.py`, and the approve endpoint dispatches
there.

`ToolSpec` in the data plane re-declares the risk level and approval
requirement rather than trusting what the engine wrote, and a parity test
(`backend/tests/test_os_tools_send_email.py`) asserts the two declarations
agree.

### Idempotency — exactly what is guaranteed

Four layers, in order:

1. **The approval claim.** `status = 'pending_approval' → 'running'` is a
   conditional UPDATE, executed *before* anything external is touched. A
   double-clicked button, a retried request and two operators approving at
   once all collapse to one winner; everyone else gets `already_decided`.
2. **The idempotency key** (optional, engine-side): a partial unique index on
   `(client_id, tool_id, idempotency_key)` means a repeated *proposal* returns
   the existing execution instead of creating a second approvable action.
3. **A Message-ID fingerprint.** Every message carries
   `Message-ID: <aos-<execution_id>@actions.agentnexlify>` — stable across
   retries of the same action, unique across different ones. Before sending,
   the tool asks Gmail `rfc822msgid:<that id>`; a hit means this exact action
   already sent, and it adopts that message rather than sending again.
4. **No automatic retry.** An unknown outcome leaves the row non-terminal with
   `send_outcome_unknown`. Nothing re-drives it on its own.

**What this is not:** exactly-once. Gmail exposes no idempotency key, so a
window remains where Gmail accepts a message and the response is lost before we
record it. In that window our record says *unknown*, never "sent" — and layer 3
closes it on the next attempt. The honest label is **at-most-once with a
resolvable unknown**.

### Verification — separate from execution

`execution_status` and `verification_status` are separate columns and separate
claims. "The API returned 200" is not verification.

The verifier fetches the sent message back by the id Gmail returned and
compares the recipient and subject against what was approved. A message that
cannot be read back, or that is addressed to someone else, ends
`status = succeeded, verification_state = failed` → the row's overall status
becomes `verification_failed`. That combination is deliberately representable:
the send happened and we could not confirm it, which the owner is told in those
words.

Providers that cannot support this are not used by this tool. Resend and the
M365 Graph path return no fetchable message id, so `send_email` refuses to run
without Gmail rather than silently sending somewhere it cannot check. The
existing `email.send` deliverable action still covers those providers.

### Two kinds of "action" in this repo

| | `os_action_runs` (migration 126) | `os_tool_executions` (migration 195) |
|---|---|---|
| What triggers it | the owner approves a **deliverable** (a drafted SMS/email) | an **agent** selects a tool mid-run |
| Chosen by | the draft's channel → `action_type` | the agent, from the typed registry |
| Has a risk level | no | yes (0-3) |
| Input schema | none (extracted from the draft) | Zod + Pydantic, validated on both planes |
| Verification | none | independent read-back |
| Still in use | yes, unchanged | yes |

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

```
pending_approval ──approve──▶ approved ──▶ running ──▶ succeeded
       │                                          ├──▶ failed
       │                                          └──▶ verification_failed
       ├──reject──▶ denied
       └──policy denial──▶ denied
(policy allows) ──▶ approved ──▶ running ──▶ …
```

`status` and `verification_state` are deliberately separate axes: "it ran" and
"we confirmed it landed" must never be conflated. A tool that runs but fails its
verifier ends `verification_failed` and returns no output to the agent — it is
never reported as success.

Exactly-once is enforced with conditional transitions, not read-then-write:

- the data plane moves a row out of `pending_approval` with a conditional
  `UPDATE ... WHERE status = 'pending_approval'` before it calls the engine, so a
  double-clicked approval never reaches the engine twice;
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

- **Gmail** — done: `send_email`, the first real external action.
- **Outlook, Google / Microsoft Calendar, CRM, invoicing** — the same shape:
  declare the tool in the engine with `implementation: "data_plane"`, add a
  module to `backend/services/os_tools/`, and the gate, the audit row and the
  two-axis verification come for free.
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
| `send_email`: gate, idempotency, provider failures, verification, tenant isolation | `backend/tests/test_os_tools_send_email.py` |
| The owner's approval surface | `frontend/src/components/os/ToolApprovalCard.test.jsx` |

Run them with `cd agent-service && npm run typecheck && npm test`, and
`python -m pytest backend/tests/test_os_tool_executions.py`. Both run in CI
(`.github/workflows/pr-check.yml`) and in `scripts/ci_local.sh`.
