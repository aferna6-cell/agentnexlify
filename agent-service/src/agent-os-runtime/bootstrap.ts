/**
 * Registers the agent-service's scoped providers with the vendored engine.
 * Idempotent; called once when the orchestrate runtime is first imported.
 */

import { setSharedContextProvider } from "../agent-os/lib/providers/shared-context.ts";
import { setRunStore } from "../agent-os/lib/providers/run-store.ts";
import { setOwnerActions } from "../agent-os/lib/providers/owner-actions.ts";
import { ScopedSharedContextProvider, ScopedRunStore, ScopedOwnerActions } from "./scoped-providers.ts";

let registered = false;

export function registerAgentOsProviders(): void {
  if (registered) return;
  setSharedContextProvider(new ScopedSharedContextProvider());
  setRunStore(new ScopedRunStore());
  setOwnerActions(new ScopedOwnerActions());
  registered = true;
}
