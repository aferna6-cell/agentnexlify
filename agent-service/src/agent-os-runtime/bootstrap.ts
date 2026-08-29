/**
 * Registers the agent-service's scoped providers with the vendored engine.
 * Idempotent; called once when the orchestrate runtime is first imported.
 */

import { setSharedContextProvider } from "../agent-os/lib/providers/shared-context.ts";
import { setRunStore } from "../agent-os/lib/providers/run-store.ts";
import { setOwnerActions } from "../agent-os/lib/providers/owner-actions.ts";
import { setActionStore } from "../agent-os/actions/store.ts";
import { setToolPorts } from "../agent-os/actions/ports.ts";
import { setToolPolicyProvider } from "../agent-os/actions/policy.ts";
import {
  ScopedSharedContextProvider,
  ScopedRunStore,
  ScopedOwnerActions,
  ScopedActionStore,
  ScopedToolPolicyProvider,
  scopedToolPorts,
} from "./scoped-providers.ts";

let registered = false;

export function registerAgentOsProviders(): void {
  if (registered) return;
  setSharedContextProvider(new ScopedSharedContextProvider());
  setRunStore(new ScopedRunStore());
  setOwnerActions(new ScopedOwnerActions());
  setActionStore(new ScopedActionStore());
  setToolPorts(scopedToolPorts);
  setToolPolicyProvider(new ScopedToolPolicyProvider());
  registered = true;
}
