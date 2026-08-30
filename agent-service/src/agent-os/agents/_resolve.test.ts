/**
 * Category tests for entity resolution.
 *
 * The property under test is that ambiguity survives as a value. Every one of
 * these has a plausible "just pick the first one" implementation that would
 * pass a happy-path suite and quietly write to the wrong customer in
 * production.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { describeAmbiguity, isResolved, resolveByName, resolveCustomerAnywhere } from "./_resolve.ts";
import type { SharedContext } from "../types/agent.ts";

const named = (...names: string[]) => names.map((name, i) => ({ id: `id_${i}`, name }));
const byName = (n: { name: string }) => n.name;

test("an exact full-name match resolves", () => {
  const r = resolveByName(named("Sarah Chen", "Mike Johnson"), byName, "Sarah Chen");
  assert.equal(r.kind, "exact");
  assert.ok(isResolved(r) && r.match.name === "Sarah Chen");
});

test("a unique partial resolves, by prefix or by whole word", () => {
  const people = named("Sarah Chen", "Mike Johnson");
  assert.equal(resolveByName(people, byName, "Sarah").kind, "unique");
  assert.equal(resolveByName(people, byName, "Chen").kind, "unique");
  assert.equal(resolveByName(people, byName, "Johnson").kind, "unique");
});

test("two people sharing a first name is ambiguous, never a pick", () => {
  const people = named("Mike Johnson", "Mike Rivera", "Sarah Chen");
  const r = resolveByName(people, byName, "Mike");
  assert.equal(r.kind, "multiple");
  assert.equal(isResolved(r), false);
  assert.ok(r.kind === "multiple" && r.matches.length === 2);
});

test("ambiguity does not fall through to a looser rule that would break the tie", () => {
  // Two exact duplicates must stay ambiguous rather than being separated by a
  // partial match further down. A looser rule cannot legitimately resolve what
  // a stricter one could not.
  const people = named("Sam Reed", "Sam Reed");
  assert.equal(resolveByName(people, byName, "Sam Reed").kind, "multiple");
});

test("a substring that is not a whole word does not match", () => {
  // "Mike" must not match "Carmike"; short queries are where a naive
  // `includes()` becomes dangerous.
  assert.equal(resolveByName(named("Carmike Braddock"), byName, "Mike").kind, "none");
});

test("resolution is case- and whitespace-insensitive", () => {
  const people = named("Sarah Chen");
  for (const q of ["sarah chen", "  Sarah   Chen ", "SARAH CHEN"]) {
    assert.equal(resolveByName(people, byName, q).kind, "exact", q);
  }
});

test("an empty query resolves to nothing rather than to everything", () => {
  assert.equal(resolveByName(named("Sarah Chen"), byName, "   ").kind, "none");
});

test("a customer known only from an invoice is still a customer", () => {
  // Refusing to act because someone is absent from the sales pipeline is a
  // resolution failure dressed up as caution.
  const context = {
    pipelineLeads: [{ id: "l1", name: "Sarah Chen", status: "new" }],
    invoices: [{ id: "i1", customerName: "Dana Whitfield", number: "INV-1", amount: 100, issuedAt: "", dueAt: "", status: "unpaid" }],
    appointments: [{ id: "a1", customerName: "Sam Reed", scheduledFor: "", status: "scheduled", reviewRequested: false }],
  } as unknown as SharedContext;

  for (const name of ["Sarah Chen", "Dana Whitfield", "Sam Reed"]) {
    assert.ok(isResolved(resolveCustomerAnywhere(context, name)), name);
  }
  assert.equal(resolveCustomerAnywhere(context, "Nobody Here").kind, "none");
});

test("the same person appearing in two sources is one customer, not an ambiguity", () => {
  const context = {
    pipelineLeads: [{ id: "l1", name: "Sarah Chen", status: "new" }],
    invoices: [{ id: "i1", customerName: "Sarah Chen", number: "INV-1", amount: 100, issuedAt: "", dueAt: "", status: "unpaid" }],
    appointments: [{ id: "a1", customerName: "Sarah Chen", scheduledFor: "", status: "scheduled", reviewRequested: false }],
  } as unknown as SharedContext;
  assert.equal(resolveCustomerAnywhere(context, "Sarah Chen").kind, "exact");
});

test("an ambiguity can be described back to the owner", () => {
  assert.equal(describeAmbiguity(named("Mike Johnson", "Mike Rivera"), byName), "Mike Johnson or Mike Rivera");
  assert.equal(
    describeAmbiguity(named("A B", "C D", "E F"), byName),
    "A B, C D, or E F",
  );
});
