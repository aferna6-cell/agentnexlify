/**
 * Milestone 8 CRM decision-path gate.
 *
 * Scores natural-language owner asks through:
 *   readAskIntent → extractParams → resolveRecordAction
 *
 * Direct executeAction() success must NEVER substitute for resolver-path
 * success. If a CRM tool exists but NL orchestration never selects it, this
 * gate fails.
 *
 *   npm run eval:crm-decision-path
 *   npm run eval:crm-decision-path:gate
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { resolveRecordAction } from "../src/agent-os/agents/admin_records_actions.ts";
import { readAskIntent, authorizesAction } from "../src/agent-os/agents/_intent.ts";
import { extractParams } from "../src/agent-os/agents/_extract.ts";
import { CRM_ACTIONS_FLAG } from "../src/agent-os/actions/flags.ts";
import type { SharedContext } from "../src/agent-os/types/agent.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const DATASET = join(
  HERE,
  "datasets/crm-decision-path/crm-decision-path-v1.json",
);
const RESULTS = join(HERE, "results");

interface Case {
  id: string;
  ask: string;
  expected_tool: string | null;
  expected_input?: Record<string, unknown>;
  expected_clarify?: boolean;
  crm_flag: "0" | "1";
}

interface Dataset {
  dataset_version: string;
  cases: Case[];
}

const context: SharedContext = {
  businessProfile: {
    businessName: "Sunset Auto Care",
    timezone: "America/Phoenix",
  },
  widgetHistory: [],
  pipelineLeads: [
    {
      id: "lead_1",
      name: "Sarah Jones",
      status: "new",
      email: "sarah@example.com",
      phone: "864-555-0100",
      address: "1 Oak St",
    },
    {
      id: "lead_2",
      name: "Mike Smith",
      status: "contacted",
      email: "mike@example.com",
      phone: "864-555-0101",
    },
    { id: "lead_3", name: "Mike Rivera", status: "new" },
  ],
  pipelineStages: ["new", "contacted", "qualified", "won", "lost"],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

function deepEqual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

function runCase(c: Case) {
  const prev = process.env[CRM_ACTIONS_FLAG];
  if (c.crm_flag === "1") process.env[CRM_ACTIONS_FLAG] = "1";
  else delete process.env[CRM_ACTIONS_FLAG];

  try {
    const intent = readAskIntent(c.ask);
    const params = extractParams(c.ask);
    const out = resolveRecordAction({
      ownerAsk: c.ask,
      params,
      context,
      intent,
    });

    const toolId = out && "toolId" in out ? (out.toolId as string) : null;
    const clarify = Boolean(out && "clarify" in out);
    const input =
      out && "input" in out
        ? (out.input as Record<string, unknown>)
        : undefined;

    const errors: string[] = [];
    if (toolId !== c.expected_tool) {
      errors.push(`tool ${toolId} !== ${c.expected_tool}`);
    }
    if (c.expected_clarify && !clarify) {
      errors.push("expected clarify");
    }
    if (c.expected_input && !deepEqual(input, c.expected_input)) {
      errors.push(
        `input ${JSON.stringify(input)} !== ${JSON.stringify(c.expected_input)}`,
      );
    }
    if (
      toolId &&
      ["create_customer", "update_customer", "update_lead_stage"].includes(
        toolId,
      ) &&
      !authorizesAction(intent)
    ) {
      errors.push("mutation selected without authorization");
    }

    return {
      id: c.id,
      ok: errors.length === 0,
      toolId,
      clarify,
      errors,
      intent: intent.intent,
      auth: authorizesAction(intent),
    };
  } finally {
    if (prev === undefined) delete process.env[CRM_ACTIONS_FLAG];
    else process.env[CRM_ACTIONS_FLAG] = prev;
  }
}

function main() {
  const gate = process.argv.includes("--gate");
  const dataset = JSON.parse(readFileSync(DATASET, "utf8")) as Dataset;
  const outcomes = dataset.cases.map(runCase);
  const pass = outcomes.filter((o) => o.ok).length;
  const fail = outcomes.filter((o) => !o.ok);

  const summary = {
    dataset_version: dataset.dataset_version,
    case_count: outcomes.length,
    pass,
    fail: fail.length,
    accuracy: Number((pass / outcomes.length).toFixed(4)),
    failures: fail,
    executor_bypassed: true,
    path: "readAskIntent → extractParams → resolveRecordAction",
  };

  mkdirSync(RESULTS, { recursive: true });
  const outPath = join(RESULTS, `crm-decision-path-v1-${Date.now()}.json`);
  writeFileSync(outPath, JSON.stringify(summary, null, 2) + "\n");
  console.log(JSON.stringify(summary, null, 2));
  console.log(`wrote ${outPath}`);

  if (gate && fail.length > 0) {
    console.error("GATE FAIL: CRM decision-path cases failed");
    process.exit(1);
  }
}

main();
