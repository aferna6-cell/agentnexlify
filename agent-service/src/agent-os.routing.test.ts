/**
 * Routing coverage (Phase 2): every department head is reachable through the
 * real orchestrator on a clearly-signaled ask. Runs offline (heuristic
 * classifier + local composer), so it's hermetic and proves the full 8-agent
 * surface routes — not just the Sales tracer.
 *
 * Lives OUTSIDE src/agent-os/ (the vendor script rm -rf's that dir).
 */

import { test } from "node:test";
import assert from "node:assert/strict";

delete process.env.ANTHROPIC_API_KEY;
delete process.env.AGENT_OS_DRAFTS_DISABLED;

import { runOrchestration } from "./agent-os-runtime/orchestrate.ts";
import type { SharedContext } from "./agent-os/types/agent.ts";

const CONTEXT: SharedContext = {
  businessProfile: { businessName: "Acme Auto", ownerName: "Sam", businessType: "auto_shop" },
  widgetHistory: [],
  pipelineLeads: [],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

// One clearly-signaled ask per department head. Heuristic routing (no API key)
// must land each on its owning department.
const CASES: { dept: string; ask: string }[] = [
  { dept: "sales", ask: "Write a sales quote for a new lead who wants an estimate on a brake job" },
  { dept: "marketing", ask: "Create a marketing campaign email promoting our spring tune-up special" },
  { dept: "customer_service", ask: "A customer asked through the widget if we service hybrids — draft a reply" },
  { dept: "operations", ask: "Book an appointment for a customer on Thursday at 2pm and send a reminder" },
  { dept: "invoicing", ask: "Send a payment reminder for the overdue invoice to the customer" },
  { dept: "accounting", ask: "Prepare a financial summary of last month's revenue for tax prep" },
  { dept: "admin_records", ask: "Draft a service contract document for a new commercial client" },
  { dept: "people", ask: "Write a job posting to hire a new auto technician for the shop" },
];

for (const { dept, ask } of CASES) {
  test(`routes to ${dept}`, async () => {
    const out = await runOrchestration({ accountId: "tenant", ask, context: CONTEXT });
    assert.equal(
      out.result.agentId,
      dept,
      `ask "${ask}" routed to ${out.result.agentId} (status ${out.result.status}), expected ${dept}`,
    );
    // The routed run is recorded for persistence.
    assert.equal(out.record.runs.at(-1)?.agentId, dept);
  });
}
