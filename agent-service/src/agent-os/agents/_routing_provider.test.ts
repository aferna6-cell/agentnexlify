/**
 * The routing provider seam is an experiment hook, and the thing that matters
 * about it is what it CANNOT do. A model that could reach policy would be a
 * model with a vote on whether it may act.
 */

import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { classify, resetRoutingProvider, setRoutingProvider, hasRoutingProvider } from "./_classifier.ts";

afterEach(() => resetRoutingProvider());

test("a registered provider decides routing", async () => {
  setRoutingProvider(() => [{ agentId: "people", confidence: 0.9, score: 9 }]);
  const out = await classify("email dana about the quote");
  assert.equal(out.classifier, "ml");
  assert.equal(out.candidates[0]!.agentId, "people");
});

test("returning nothing falls through to the shipped router", async () => {
  setRoutingProvider(() => null);
  const out = await classify("post a hiring ad for a mechanic");
  assert.equal(out.classifier, "heuristic", "an empty provider must not blank the router");
  assert.equal(out.candidates[0]!.agentId, "people");
});

test("the seam is off by default and resets cleanly", async () => {
  assert.equal(hasRoutingProvider(), false);
  setRoutingProvider(() => [{ agentId: "sales", confidence: 1, score: 20 }]);
  assert.equal(hasRoutingProvider(), true);
  resetRoutingProvider();
  assert.equal(hasRoutingProvider(), false);
  const out = await classify("chase the overdue invoice");
  assert.notEqual(out.classifier, "ml");
});

test("a provider still cannot make an unauthorized ask into an action", async () => {
  // Route a draft-only request to Sales with maximum confidence. Routing is all
  // the provider controls: authorization, approval and execution are decided
  // downstream by policy that never consults it.
  const { harness } = await import("../actions/_testkit.ts");
  const { createTraceEmitter } = await import("./_trace.ts");
  const { extractParams } = await import("./_extract.ts");
  const { sales } = await import("./departments.ts");

  const h = harness();
  setRoutingProvider(() => [{ agentId: "sales", confidence: 1, score: 99 }]);

  const ask = "Draft an email to dana@example.com about her quote, I'll review it first.";
  await sales.run({
    input: extractParams(ask),
    context: h.context,
    emitTrace: createTraceEmitter("run_1", { persist: false }),
    ownerAsk: ask,
    runId: "run_1",
    userId: "tenantA",
  });

  assert.deepEqual(
    await h.store.list({ accountId: "tenantA" }),
    [],
    "a confident route must not authorize a send the owner did not ask for",
  );
});
