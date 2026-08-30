/**
 * Fail-closed lock: this runner must never write live os_tool_executions.
 *
 * Allowed executor: InMemoryActionStore + InMemoryCustomerNotesPort + FakeGmailPort.
 * Anything that could reach the FastAPI/Supabase persist path aborts.
 */

import {
  InMemoryCustomerNotesPort,
  getToolPorts,
} from "../../src/agent-os/actions/ports.ts";
import {
  InMemoryActionStore,
  getActionStore,
} from "../../src/agent-os/actions/store.ts";
import { FakeGmailPort } from "./fake-gmail-port.ts";

export class LiveOsToolExecutionAbort extends Error {
  constructor(reason: string) {
    super(
      `LIVE os_tool_executions write path aborted: ${reason}. ` +
        "This runner allows InMemoryActionStore + FakeGmailPort only.",
    );
    this.name = "LiveOsToolExecutionAbort";
  }
}

/** Import / call-site patterns that can persist into the production table. */
export const FORBIDDEN_LIVE_PERSIST_MARKERS = [
  "runOrchestration",
  "agent-os-runtime/orchestrate",
  "agent-os-runtime/bootstrap",
  "agent-os-runtime/action-collector",
  "agent-os-runtime/approve-action",
  "CollectingActionStore",
  "ScopedActionStore",
  "CollectingCustomerNotesPort",
  "persist_tool_executions",
  "backend/services/os_tool_executions",
  "@supabase/supabase-js",
] as const;

export function assertNoLivePersistImports(
  source: string,
  label: string,
): void {
  for (const marker of FORBIDDEN_LIVE_PERSIST_MARKERS) {
    if (source.includes(marker)) {
      throw new LiveOsToolExecutionAbort(
        `${label} contains a live persist marker (${marker})`,
      );
    }
  }
}

export function assertEvalOnlyExecutor(
  store: unknown,
  notes: unknown,
  gmail: unknown,
): void {
  if (!(store instanceof InMemoryActionStore)) {
    throw new LiveOsToolExecutionAbort(
      "ActionStore is not InMemoryActionStore — refusing a path that could persist live rows",
    );
  }
  if (
    !(notes instanceof InMemoryCustomerNotesPort) ||
    notes.durable !== false
  ) {
    throw new LiveOsToolExecutionAbort(
      "notes port is not the non-durable in-memory port",
    );
  }
  if (!(gmail instanceof FakeGmailPort) || gmail.durable !== false) {
    throw new LiveOsToolExecutionAbort("Gmail boundary is not FakeGmailPort");
  }
  const registered = getActionStore();
  if (registered !== store) {
    throw new LiveOsToolExecutionAbort(
      "registered ActionStore is not the eval in-memory instance",
    );
  }
  const ports = getToolPorts();
  if (ports.customerNotes !== notes) {
    throw new LiveOsToolExecutionAbort(
      "registered notes port is not the eval in-memory instance",
    );
  }
}
