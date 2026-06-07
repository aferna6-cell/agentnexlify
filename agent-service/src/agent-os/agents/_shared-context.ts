/**
 * Shared-context wiring for the agent-service runtime.
 *
 * The standalone registers a Prisma provider here; the agent-service registers
 * its production SharedContextProvider at startup (reading the FastAPI/Supabase
 * data plane, scoped by client_id). This module only keeps `loadSharedContext()`
 * as the stable accessor the orchestrator imports — identical signature to the
 * standalone, so the vendored orchestrator is unchanged.
 */

import { getSharedContextProvider } from "../lib/providers/shared-context.ts";
import type { SharedContext } from "../types/agent.ts";

export async function loadSharedContext(userId: string): Promise<SharedContext> {
  return getSharedContextProvider().load(userId);
}
