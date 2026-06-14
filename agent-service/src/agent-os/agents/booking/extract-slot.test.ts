import { test } from "node:test";
import assert from "node:assert/strict";
import { extractSlot } from "./extract-slot.ts";

test("extracts day + time from owner text", () => {
  assert.equal(
    extractSlot("Draft a confirmation — tire rotation Thursday at 10:30 AM"),
    "Thursday at 10:30 AM",
  );
});

test("normalizes lowercase am/pm and spacing", () => {
  assert.equal(extractSlot("see you saturday 9am"), "Saturday at 9AM");
});

test("day only when no time present", () => {
  assert.equal(extractSlot("can we do Tuesday?"), "Tuesday");
});

test("time only when no day present", () => {
  assert.equal(extractSlot("how about 2pm"), "2PM");
});

test("handles abbreviations", () => {
  assert.equal(extractSlot("thurs at 3:00 PM works"), "Thursday at 3:00 PM");
});

test("returns undefined with no day or time", () => {
  assert.equal(extractSlot("please book the customer in"), undefined);
  assert.equal(extractSlot(undefined), undefined);
});
