/**
 * "What can you help me with?" is a product question, not a missed department.
 * The owner should get a capabilities list, never backlog jargon.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

delete process.env.ANTHROPIC_API_KEY;
delete process.env.AGENT_OS_DRAFTS_DISABLED;

import { runOrchestration } from "./agent-os-runtime/orchestrate.ts";
import {
  capabilitiesAnswer,
  isCapabilityAsk,
} from "./agent-os/agents/_capabilities.ts";
import type { SharedContext } from "./agent-os/types/agent.ts";

const CONTEXT: SharedContext = {
  businessProfile: {
    businessName: "Acme Auto",
    ownerName: "Sam",
    businessType: "auto_shop",
  },
  widgetHistory: [],
  pipelineLeads: [],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

test("capability phrasing is recognized", () => {
  assert.equal(isCapabilityAsk("What can you help me with?"), true);
  assert.equal(isCapabilityAsk("what can you do"), true);
  assert.equal(isCapabilityAsk("How can you help?"), true);
  assert.equal(isCapabilityAsk("Draft a follow-up for Mike"), false);
});

test("the capabilities list is plain English with example prompts", () => {
  const text = capabilitiesAnswer();
  assert.match(text, /Follow up with leads/);
  assert.match(text, /Prepare my weekly business summary/);
  assert.doesNotMatch(text, /orchestrator/i);
  assert.doesNotMatch(text, /wishlist/i);
});

test("a capability question is answered directly", async () => {
  const out = await runOrchestration({
    accountId: "tenant",
    ask: "What can you help me with?",
    context: CONTEXT,
  });
  assert.equal(out.result.status, "direct_answer");
  const text = `${out.result.answer ?? ""}\n${(out.result.orchestratorNotes || []).join("\n")}`;
  assert.match(text, /example you can paste/);
  assert.match(text, /Draft a friendly follow-up/);
  assert.doesNotMatch(text, /wishlist/i);
  assert.doesNotMatch(text, /orchestrator/i);
  assert.doesNotMatch(text, /department/i);
});

test("a miss does not tell the owner it was saved to a wishlist", async () => {
  const out = await runOrchestration({
    accountId: "tenant",
    ask: "blorp the snizzle please",
    context: CONTEXT,
  });
  const text = `${out.result.answer ?? ""}\n${(out.result.orchestratorNotes || []).join("\n")}`;
  assert.doesNotMatch(text, /wishlist/i);
  assert.doesNotMatch(text, /orchestrator/i);
});
