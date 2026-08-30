import { test } from "node:test";
import assert from "node:assert/strict";
import { readAskIntent } from "./_intent.ts";
import {
  resolveCommunicationAmbiguity,
  soleRecipient,
} from "./communication_actions.ts";
import type { SharedContext } from "../types/agent.ts";

const context: SharedContext = {
  businessProfile: { businessName: "Acme" },
  widgetHistory: [],
  pipelineLeads: [
    { id: "1", name: "Mike Johnson", status: "quoted", quoteAmount: 100 },
    { id: "2", name: "Mike Rivera", status: "quoted", quoteAmount: 200 },
  ],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

test("soleRecipient refuses when two addresses are present", () => {
  assert.equal(soleRecipient("email a@x.com and b@y.com"), undefined);
  assert.equal(
    soleRecipient("email sarah@example.com about the quote"),
    "sarah@example.com",
  );
});

test("ambiguous Mike asks for clarification instead of guessing", () => {
  const ask = "Email Mike about the quote";
  const intent = readAskIntent(ask);
  const out = resolveCommunicationAmbiguity({
    ownerAsk: ask,
    params: { customer_name: "Mike" },
    context,
    intent,
    departmentId: "sales",
  });
  assert.ok(out && "clarify" in out);
  assert.match((out as { clarify: string }).clarify, /more than one/i);
});
