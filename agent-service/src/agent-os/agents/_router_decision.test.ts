/**
 * Tests for the observable routing decision.
 *
 * The load-bearing property is not that the fields get populated — it is that
 * two numbers which mean different things stay in different fields, and that a
 * decision confers no authority beyond picking a department.
 */

import { strict as assert } from "node:assert";
import { describe, it } from "node:test";

import { fromClassification, asClarification } from "./_router_decision.ts";
import type { Classification } from "./_classifier.ts";

const heuristicCls: Classification = {
  classifier: "heuristic",
  candidates: [
    { agentId: "sales", confidence: 0.8, score: 8 },
    { agentId: "invoicing", confidence: 0.5, score: 2 },
  ],
  params: {},
};

const haikuCls: Classification = {
  classifier: "haiku",
  candidates: [{ agentId: "operations", confidence: 0.91 }],
  params: {},
};

describe("RouterDecision", () => {
  it("keeps the heuristic's raw evidence, not its saturated confidence", () => {
    const d = fromClassification(heuristicCls);
    // 8, the evidence — NOT 0.8, which is score/(score+2) and is the number the
    // orchestrator deliberately does not threshold on.
    assert.equal(d.rawScore, 8);
    assert.equal(d.department, "sales");
    assert.equal(d.source, "heuristic");
  });

  it("uses the probability as the raw score where there is no evidence scale", () => {
    const d = fromClassification(haikuCls);
    assert.equal(d.rawScore, 0.91);
    assert.equal(d.source, "haiku");
  });

  it("reports calibratedConfidence as null rather than echoing the raw score", () => {
    // The engine ships no calibrator. Null is the accurate statement; copying
    // rawScore here would create a number a threshold could later be written
    // against, which is the exact failure the two-field split exists to prevent.
    for (const cls of [heuristicCls, haikuCls]) {
      const d = fromClassification(cls);
      assert.equal(d.calibratedConfidence, null);
      assert.notEqual(d.calibratedConfidence, d.rawScore);
    }
  });

  it("abstains when nothing scored, and says why", () => {
    const d = fromClassification({ classifier: "heuristic", candidates: [], params: {} });
    assert.equal(d.department, null);
    assert.equal(d.abstained, true);
    assert.equal(d.source, "owner_clarification");
    assert.equal(d.escalationReason, "heuristic_no_candidate");
  });

  it("records an ambiguity clarification without losing the candidates", () => {
    const d = asClarification(heuristicCls, "candidates_indistinguishable");
    assert.equal(d.department, null);
    assert.equal(d.abstained, true);
    assert.equal(d.escalationReason, "candidates_indistinguishable");
    // Both options survive: the owner is about to be shown them.
    assert.deepEqual(d.alternates.map((c) => c.agentId), ["sales", "invoicing"]);
  });

  it("carries per-stage scores so a confident-and-wrong route is distinguishable from a silent one", () => {
    const confident = fromClassification(heuristicCls);
    const silent = fromClassification({ classifier: "heuristic", candidates: [], params: {} });
    assert.equal(confident.stageScores.heuristic, 8);
    assert.deepEqual(silent.stageScores, {});
  });

  it("exposes no field that could carry policy authority", () => {
    // A RouterDecision picks a department. Approval, risk level, tool choice,
    // tenant scope and verification are decided elsewhere and must not become
    // reachable from routing output by accident.
    const forbidden = [
      "approved", "approvalState", "requiresApproval", "riskLevel", "risk",
      "tool", "toolId", "canExecute", "execute", "tenantId", "userId",
      "verified", "verificationState", "policy", "allowed",
    ];
    const keys = Object.keys(fromClassification(heuristicCls));
    for (const f of forbidden) {
      assert.ok(!keys.includes(f), `RouterDecision must not expose "${f}"`);
    }
  });

  it("a maximally confident decision is still only a department", () => {
    const d = fromClassification({
      classifier: "ml",
      candidates: [{ agentId: "sales", confidence: 1.0, score: 999 }],
      params: {},
    });
    assert.equal(d.department, "sales");
    assert.equal(d.source, "ml");
    // Nothing about the shape changes at confidence 1.0.
    assert.deepEqual(Object.keys(d).sort(), Object.keys(fromClassification(heuristicCls)).sort());
  });
});
