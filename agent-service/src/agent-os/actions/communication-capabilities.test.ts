import { afterEach, test } from "node:test";
import assert from "node:assert/strict";

import { DEPARTMENTS } from "../agents/departments.ts";
import {
  SEND_EMAIL_CAPABLE_DEPARTMENTS,
  canProposeSendEmail,
} from "./communication-capabilities.ts";
import { SEND_EMAIL_FLAG } from "./flags.ts";
import { evaluateActionPolicy } from "./policy.ts";
import { sendEmail } from "./tools/send_email.ts";

const previousFlag = process.env[SEND_EMAIL_FLAG];

afterEach(() => {
  if (previousFlag === undefined) delete process.env[SEND_EMAIL_FLAG];
  else process.env[SEND_EMAIL_FLAG] = previousFlag;
});

test("communication action wiring matches the explicit capability list", () => {
  const wired = DEPARTMENTS.filter(
    (department) =>
      department.__department.resolveActionFromOutput !== undefined,
  ).map((department) => department.agent_id);

  assert.deepEqual(wired.sort(), [...SEND_EMAIL_CAPABLE_DEPARTMENTS].sort());
});

test("send_email policy permits only explicitly capable departments", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  for (const department of DEPARTMENTS) {
    const allowed = canProposeSendEmail(department.agent_id);
    const evaluation = evaluateActionPolicy(
      sendEmail,
      {},
      {
        accountId: "tenant-a",
        agentId: department.agent_id,
      },
    );
    assert.equal(
      evaluation.decision,
      allowed ? "requires_approval" : "deny",
      department.agent_id,
    );
  }
});
