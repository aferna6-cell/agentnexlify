/**
 * Multi-tenant isolation gate (Phase 1 tracer bullet).
 *
 * Runs the REAL vendored orchestrator against two tenants through in-memory
 * providers, asserting:
 *   1. a clearly-sales ask routes to the Sales department;
 *   2. each handle() loads ONLY the calling tenant's context (no cross-tenant
 *      read) — the highest-stakes property of the merge;
 *   3. every run is tagged with the calling tenant's id;
 *   4. an unknown tenant can load no context at all.
 *
 * Runs fully offline (no ANTHROPIC_API_KEY): the classifier falls back to the
 * heuristic and agents use the deterministic local composer, so this is
 * hermetic. This is the engine-boundary proof that production's HttpProviders
 * (scoped by client_id) must preserve.
 *
 * Lives OUTSIDE src/agent-os/ because the vendor script (scripts/vendor-agent-os.sh)
 * rm -rf's that directory on every re-vendor.
 */

import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";

// Force offline so routing + drafting are deterministic.
delete process.env.ANTHROPIC_API_KEY;
delete process.env.AGENT_OS_DRAFTS_DISABLED;

import { handle } from "./agent-os/agents/_orchestrator.ts";
import { setSharedContextProvider, type SharedContextProvider } from "./agent-os/lib/providers/shared-context.ts";
import { setRunStore, type RunStore } from "./agent-os/lib/providers/run-store.ts";
import { setOwnerActions } from "./agent-os/lib/providers/owner-actions.ts";
import type { SharedContext } from "./agent-os/types/agent.ts";

function ctxFor(businessName: string): SharedContext {
  return {
    businessProfile: { businessName, ownerName: "Owner", businessType: "auto_shop" },
    widgetHistory: [],
    pipelineLeads: [],
    appointments: [],
    invoices: [],
    agentRunHistory: [],
    kb: [],
  };
}

const CONTEXTS: Record<string, SharedContext> = {
  tenantA: ctxFor("Acme Auto"),
  tenantB: ctxFor("Bob Plumbing"),
};

let loads: string[] = [];
let runs: { userId: string; agentId: string }[] = [];

const provider: SharedContextProvider = {
  async load(userId: string): Promise<SharedContext> {
    loads.push(userId);
    const c = CONTEXTS[userId];
    if (!c) throw new Error(`isolation breach: context requested for unknown tenant ${userId}`);
    return c;
  },
};

const store: RunStore = {
  async createRoutingDecision() { return { id: `rd-${Math.random()}` }; },
  async markRoutingDecisionOverridden() {},
  async createRun(input) { runs.push({ userId: input.userId, agentId: input.agentId }); return { id: `run-${runs.length}` }; },
  async setRunStatus() {},
  async createDraft() { return { id: `draft-${Math.random()}` }; },
  async captureWishlist() {},
  async recordTraceStep() {},
  async logModelCall() {},
};

setSharedContextProvider(provider);
setRunStore(store);
setOwnerActions({ async tagAiVisibilityInterest() { return true; } });

beforeEach(() => {
  loads = [];
  runs = [];
});

test("a clear sales ask routes to the Sales department", async () => {
  const res = await handle("tenantA", "Write a sales quote for a new customer lead who wants a brake job");
  assert.equal(res.agentId, "sales", `expected routing to sales, got ${res.agentId} (status ${res.status})`);
  assert.deepEqual([...new Set(loads)], ["tenantA"]);
  assert.equal(runs.at(-1)?.userId, "tenantA");
});

test("two tenants never load each other's context (isolation gate)", async () => {
  // forceAgentId removes routing ambiguity so this asserts the data-scoping
  // property directly: each run loads exactly one tenant's context.
  await handle("tenantA", "Draft a quote follow-up", { forceAgentId: "sales" });
  await handle("tenantB", "Draft a quote follow-up", { forceAgentId: "sales" });

  assert.deepEqual(loads, ["tenantA", "tenantB"], "each handle must load exactly its own tenant, in order");
  assert.equal(runs.length, 2);
  assert.equal(runs[0]?.userId, "tenantA");
  assert.equal(runs[1]?.userId, "tenantB");
  assert.notEqual(runs[0]?.userId, runs[1]?.userId);
});

test("an unknown tenant cannot load any context", async () => {
  await assert.rejects(
    () => handle("tenantC", "Draft a quote follow-up", { forceAgentId: "sales" }),
    /isolation breach: context requested for unknown tenant tenantC/,
  );
});
