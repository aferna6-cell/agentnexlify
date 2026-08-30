/**
 * Milestone 8 Calendar + CRM eval runner.
 *
 * Scores fixture cases through executeAction (Action Executor + policy +
 * verification). Does not enable production flags.
 *
 *   npm run eval:calendar-crm
 *   npm run eval:calendar-crm -- --gate
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import {
  executeAction,
  approveAction,
} from "../src/agent-os/actions/executor.ts";
import {
  CALENDAR_ACTIONS_FLAG,
  CRM_ACTIONS_FLAG,
} from "../src/agent-os/actions/flags.ts";
import { harness } from "../src/agent-os/actions/_testkit.ts";
import type { SharedContext } from "../src/agent-os/types/agent.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const DATASET = join(HERE, "datasets/calendar-crm/calendar-crm-eval-v1.json");
const RESULTS = join(HERE, "results");

interface Fixture {
  tool: string;
  input: Record<string, unknown>;
  expect_status: string;
  expect_verified?: boolean;
  expect_error_code?: string;
  expect_output_kind?: string;
  expect_email_preserved?: string;
  expect_deduplicated?: boolean;
  expect_single_event_title?: string;
  seed_event?: Record<string, unknown>;
  seed_create?: { name: string; email: string };
  calendar_flag?: string;
  crm_flag?: string;
  approve?: boolean;
  repeat?: number;
}

interface EvalCase {
  id: string;
  ask: string;
  category: string;
  expected_tool: string;
  expected_risk_level?: number;
  expected_requires_approval?: boolean;
  must_not_execute_without_approval?: boolean;
  tags: string[];
  fixture: Fixture;
}

interface Dataset {
  dataset_version: string;
  business_context: SharedContext;
  cases: EvalCase[];
  case_count: number;
}

async function runCase(c: EvalCase, business: SharedContext) {
  const h = harness();
  h.context = {
    ...business,
    pipelineLeads: business.pipelineLeads ?? h.context.pipelineLeads,
    pipelineStages: business.pipelineStages ?? h.context.pipelineStages,
    businessProfile: {
      ...h.context.businessProfile,
      ...business.businessProfile,
    },
  };
  // Re-seed CRM for this business context
  for (const lead of h.context.pipelineLeads) {
    h.crm.seed({
      id: lead.id,
      accountId: "tenantA",
      name: lead.name,
      status: lead.status,
      email: lead.email,
      phone: lead.phone,
      subject: lead.subject,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
  }

  const prevCal = process.env[CALENDAR_ACTIONS_FLAG];
  const prevCrm = process.env[CRM_ACTIONS_FLAG];
  process.env[CALENDAR_ACTIONS_FLAG] = c.fixture.calendar_flag ?? "1";
  process.env[CRM_ACTIONS_FLAG] = c.fixture.crm_flag ?? "1";

  try {
    if (c.fixture.seed_event) {
      h.calendar.seedEvent(c.fixture.seed_event as never);
    }
    if (c.fixture.seed_create) {
      await h.crm.createCustomer({
        accountId: "tenantA",
        name: c.fixture.seed_create.name,
        email: c.fixture.seed_create.email,
      });
    }

    const times = c.fixture.repeat ?? 1;
    let last = await executeAction({
      accountId: "tenantA",
      agentId: "admin_records",
      toolId: c.fixture.tool,
      input: c.fixture.input,
      sharedContext: h.context,
      registry: h.registry,
    });
    for (let i = 1; i < times; i++) {
      last = await executeAction({
        accountId: "tenantA",
        agentId: "admin_records",
        toolId: c.fixture.tool,
        input: c.fixture.input,
        sharedContext: h.context,
        registry: h.registry,
      });
    }

    if (c.fixture.approve && last.status === "pending_approval") {
      last = await approveAction({
        accountId: "tenantA",
        executionId: last.executionId,
        approvedBy: "owner",
        sharedContext: h.context,
        registry: h.registry,
      });
    }

    const errors: string[] = [];
    if (last.status !== c.fixture.expect_status) {
      errors.push(`status ${last.status} !== ${c.fixture.expect_status}`);
    }
    if (
      c.fixture.expect_verified &&
      last.record.verificationState !== "passed"
    ) {
      errors.push(`verification ${last.record.verificationState}`);
    }
    if (
      c.fixture.expect_error_code &&
      last.record.error?.code !== c.fixture.expect_error_code
    ) {
      errors.push(
        `error ${last.record.error?.code} !== ${c.fixture.expect_error_code}`,
      );
    }
    if (c.fixture.expect_output_kind) {
      const kind = (last.output as { kind?: string } | undefined)?.kind;
      if (kind !== c.fixture.expect_output_kind) {
        errors.push(`kind ${kind} !== ${c.fixture.expect_output_kind}`);
      }
    }
    if (c.fixture.expect_email_preserved) {
      const email = (last.output as { email?: string } | undefined)?.email;
      if (email !== c.fixture.expect_email_preserved) {
        errors.push(`email not preserved (${email})`);
      }
    }
    if (c.fixture.expect_deduplicated) {
      const dedup = (last.output as { deduplicated?: boolean } | undefined)
        ?.deduplicated;
      if (!dedup) errors.push("expected deduplicated");
    }
    if (c.fixture.expect_single_event_title) {
      const matches = h.calendar
        .allEvents()
        .filter((e) => e.title === c.fixture.expect_single_event_title);
      if (matches.length !== 1) {
        errors.push(`expected 1 event, got ${matches.length}`);
      }
    }
    if (
      c.expected_risk_level !== undefined &&
      last.record.riskLevel !== c.expected_risk_level &&
      last.status !== "denied"
    ) {
      // Denied paths keep tool risk; only score when execution progressed.
      if (last.status !== "failed") {
        errors.push(
          `risk ${last.record.riskLevel} !== ${c.expected_risk_level}`,
        );
      }
    }
    if (
      c.expected_requires_approval === true &&
      last.status !== "pending_approval" &&
      last.status !== "denied" &&
      !c.fixture.approve
    ) {
      if (last.status === "succeeded") {
        errors.push("executed without required approval");
      }
    }

    return {
      id: c.id,
      category: c.category,
      ok: errors.length === 0,
      status: last.status,
      errors,
      unsafe:
        Boolean(c.must_not_execute_without_approval) &&
        ["succeeded", "verification_failed", "running"].includes(last.status) &&
        !c.fixture.approve,
    };
  } finally {
    if (prevCal === undefined) delete process.env[CALENDAR_ACTIONS_FLAG];
    else process.env[CALENDAR_ACTIONS_FLAG] = prevCal;
    if (prevCrm === undefined) delete process.env[CRM_ACTIONS_FLAG];
    else process.env[CRM_ACTIONS_FLAG] = prevCrm;
  }
}

async function main() {
  const gate = process.argv.includes("--gate");
  const dataset = JSON.parse(readFileSync(DATASET, "utf8")) as Dataset;
  const outcomes = [];
  for (const c of dataset.cases) {
    outcomes.push(await runCase(c, dataset.business_context));
  }
  const pass = outcomes.filter((o) => o.ok).length;
  const fail = outcomes.filter((o) => !o.ok);
  const unsafe = outcomes.filter((o) => o.unsafe);
  const byCat: Record<string, { pass: number; total: number }> = {};
  for (const o of outcomes) {
    const b = (byCat[o.category] ??= { pass: 0, total: 0 });
    b.total += 1;
    if (o.ok) b.pass += 1;
  }

  const summary = {
    dataset_version: dataset.dataset_version,
    case_count: outcomes.length,
    pass,
    fail: fail.length,
    accuracy: Number((pass / outcomes.length).toFixed(4)),
    unsafe_actions: unsafe.length,
    by_category: byCat,
    failures: fail.slice(0, 30),
  };

  mkdirSync(RESULTS, { recursive: true });
  const outPath = join(RESULTS, `calendar-crm-eval-v1-${Date.now()}.json`);
  writeFileSync(outPath, JSON.stringify(summary, null, 2) + "\n");
  console.log(JSON.stringify(summary, null, 2));
  console.log(`wrote ${outPath}`);

  if (gate) {
    if (unsafe.length > 0) {
      console.error("GATE FAIL: unsafe calendar/CRM actions > 0");
      process.exit(1);
    }
    if (pass / outcomes.length < 0.95) {
      console.error("GATE FAIL: accuracy < 0.95");
      process.exit(1);
    }
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
