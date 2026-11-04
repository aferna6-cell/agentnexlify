/**
 * The weekly business summary starter used to be forced into Operations.
 * Operations' default skill is booking, and the word "bookings" inside the
 * summary prompt made it draft a customer appointment instead of a summary.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

delete process.env.ANTHROPIC_API_KEY;
delete process.env.AGENT_OS_DRAFTS_DISABLED;

import { runOrchestration } from "./agent-os-runtime/orchestrate.ts";
import { isAggregateBriefingQuery } from "./agent-os/agents/_orchestrator.ts";
import type { SharedContext } from "./agent-os/types/agent.ts";

const WEEKLY =
  "Prepare my weekly business summary: leads, bookings, conversations, and anything that needs my attention. Keep it to a scannable one-pager.";

const CONTEXT: SharedContext = {
  businessProfile: {
    businessName: "North Dock Warehouse",
    ownerName: "Sam",
    businessType: "warehouse",
  },
  widgetHistory: [],
  pipelineLeads: [],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

test("a weekly business summary is recognized as a summary", () => {
  assert.equal(isAggregateBriefingQuery(WEEKLY), true);
  assert.equal(
    isAggregateBriefingQuery(
      "Prepare my daily business summary of shipments and stock.",
    ),
    true,
  );
  assert.equal(
    isAggregateBriefingQuery("Confirm Maria's Saturday appointment."),
    false,
  );
});

test("a forced operations run still returns a summary, not an appointment draft", async () => {
  const out = await runOrchestration({
    accountId: "tenant",
    ask: WEEKLY,
    context: CONTEXT,
    forceAgentId: "operations",
  });
  assert.equal(out.result.status, "direct_answer");
  const text = `${out.result.answer ?? ""}\n${out.result.draft?.body ?? ""}`;
  assert.match(text, /briefing|Quiet week/i);
  assert.doesNotMatch(text, /your appointment/i);
  assert.equal(out.result.draft, undefined);
});
