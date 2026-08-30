/**
 * Stage-based error taxonomy for the action benchmark.
 *
 * Every failure is attributed to the EARLIEST stage of the decision pipeline
 * where it originated, not to each symptom it produced downstream. A run that
 * routed to the wrong department and therefore took no action is one routing
 * failure, not a routing failure plus an action failure plus a tool failure —
 * counting it three times would make routing look one-third as important as it
 * is, and would send the next fix to the wrong place.
 *
 * Usage:
 *   npm run eval:errors                 # validation split (the iteration set)
 *   npm run eval:errors -- --dataset <path>
 *   npm run eval:errors -- --cases      # list every failure with its stage
 */

import { loadDataset, runCase, type CaseOutcome, type EvalCase } from "./lib/eval-core.ts";

/** Pipeline stages, in the order a request passes through them. */
export const STAGES = [
  "routing",
  "intent_behavior",
  "context_resolution",
  "skill_selection",
  "skill_contract_mismatch",
  "action_resolution",
  "tool_selection",
  "parameter_extraction",
  "policy_approval",
  "harness_defect",
] as const;

export type Stage = (typeof STAGES)[number];

export interface Attribution {
  stage: Stage;
  /** The specific mechanism, for grouping inside a stage. */
  detail: string;
  /** Symptoms this one root cause also produced, which are NOT counted again. */
  cascaded: string[];
}

/** Skills whose contract is "make a new business object", not "communicate". */
const GENERATIVE_SKILLS = /quote generation|invoice|document|job post|campaign/i;

/**
 * Attribute one failing outcome to the stage that caused it.
 *
 * Ordered earliest-stage-first: the first rule that matches owns the failure,
 * and everything it explains downstream is recorded as cascade, not as a
 * separate count.
 */
export function attribute(c: EvalCase, o: CaseOutcome): Attribution | null {
  const symptoms: string[] = [];
  if (!o.department_ok) symptoms.push("wrong department");
  if (!o.behavior_ok) symptoms.push(`behavior ${o.expected_behavior}→${o.actual_behavior}`);
  if (o.tool_ok === false) symptoms.push(`tool ${o.expected_tool}→${o.actual_tool ?? "none"}`);
  if (o.params_ok === false) symptoms.push("parameters");
  if (o.approval_ok === false) symptoms.push("approval");
  if (symptoms.length === 0) return null;

  const cascaded = symptoms.slice(1);

  // 0. The run threw. Not a decision failure at all.
  if (o.actual_behavior === "error") {
    return { stage: "harness_defect", detail: `run threw: ${o.error ?? "unknown"}`, cascaded };
  }

  // 1. Routing. Everything downstream of a wrong department is downstream of
  //    this, because a department can only choose among its own skills+tools.
  if (!o.department_ok) {
    return {
      stage: "routing",
      detail: `expected ${o.expected_department}, got ${o.actual_department}`,
      cascaded: symptoms.filter((s) => s !== "wrong department"),
    };
  }

  // From here the department is right, so the failure is inside it.

  // 2. Context resolution. The label says the system should have stopped for
  //    missing or ambiguous information and it did not, or it stopped when the
  //    entity was in fact resolvable.
  if (!o.behavior_ok && c.expected_behavior === "clarification") {
    return {
      stage: "context_resolution",
      detail: `missing/ambiguous data not detected (answered ${o.actual_behavior})`,
      cascaded,
    };
  }

  // 3. Skill contract mismatch. A skill ran and refused because the inputs it
  //    demands are not the inputs this request carries — the classic
  //    "no line items provided" on a request that never asked for a new quote.
  if (o.no_draft_reason && GENERATIVE_SKILLS.test(o.skill ?? "") && c.expected_behavior !== "draft_only") {
    return {
      stage: "skill_contract_mismatch",
      detail: `${o.skill ?? "skill"} refused: ${o.no_draft_reason.slice(0, 60)}`,
      cascaded,
    };
  }

  // 4. Skill selection. A generative skill was chosen for a communicate-shaped
  //    request even though it managed to produce something.
  if (!o.behavior_ok && c.expected_behavior === "action" && GENERATIVE_SKILLS.test(o.skill ?? "")) {
    return { stage: "skill_selection", detail: `communication ask dispatched to ${o.skill}`, cascaded };
  }

  // 5. Action resolution. The department understood it and produced work, but
  //    never turned it into a tool proposal.
  if (c.expected_behavior === "action" && o.actual_tool === null) {
    return {
      stage: "action_resolution",
      detail:
        o.actual_behavior === "draft_only"
          ? "drafted instead of proposing an action"
          : `no action proposed (${o.actual_behavior})`,
      cascaded,
    };
  }

  // 6. Intent/behaviour. Acted or drafted where the label wanted something else,
  //    with no more specific cause above.
  if (!o.behavior_ok) {
    return {
      stage: "intent_behavior",
      detail: `expected ${o.expected_behavior}, got ${o.actual_behavior}`,
      cascaded,
    };
  }

  // 7. Tool selection: acting was right, the tool was not.
  if (o.tool_ok === false) {
    return { stage: "tool_selection", detail: `expected ${o.expected_tool}, got ${o.actual_tool}`, cascaded };
  }

  // 8. Policy/approval.
  if (o.approval_ok === false) {
    return { stage: "policy_approval", detail: "approval requirement mismatched the label", cascaded };
  }

  // 9. Parameters: everything upstream was right.
  return {
    stage: "parameter_extraction",
    detail: `${o.param_fields_ok}/${o.param_fields_total} required fields extracted`,
    cascaded,
  };
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const dsArg = args.indexOf("--dataset");
  const dataset = loadDataset(dsArg >= 0 ? args[dsArg + 1] : undefined);
  const listCases = args.includes("--cases");

  const rows: { c: EvalCase; o: CaseOutcome; a: Attribution }[] = [];
  let passed = 0;
  for (const c of dataset.cases) {
    const o = await runCase(c, dataset.business_context);
    const a = attribute(c, o);
    if (!a) passed++;
    else rows.push({ c, o, a });
  }

  const n = dataset.cases.length;
  console.log(`\nError taxonomy — ${dataset.dataset_version}`);
  console.log(`  ${passed}/${n} cases fully correct, ${rows.length} failing\n`);

  const byStage = new Map<Stage, typeof rows>();
  for (const r of rows) {
    const list = byStage.get(r.a.stage) ?? [];
    list.push(r);
    byStage.set(r.a.stage, list);
  }

  console.log("  stage                      failures   % of failures   % of all cases");
  for (const stage of STAGES) {
    const list = byStage.get(stage);
    if (!list?.length) continue;
    const pctFail = ((list.length / rows.length) * 100).toFixed(1);
    const pctAll = ((list.length / n) * 100).toFixed(1);
    console.log(`  ${stage.padEnd(26)} ${String(list.length).padStart(5)}   ${pctFail.padStart(10)}%   ${pctAll.padStart(11)}%`);
  }

  const cascadeCount = rows.reduce((s, r) => s + r.a.cascaded.length, 0);
  console.log(
    `\n  ${cascadeCount} downstream symptom(s) attributed to an upstream root cause rather than counted separately.`,
  );

  console.log("\nMechanisms within each stage:");
  for (const stage of STAGES) {
    const list = byStage.get(stage);
    if (!list?.length) continue;
    const details = new Map<string, number>();
    for (const r of list) details.set(r.a.detail, (details.get(r.a.detail) ?? 0) + 1);
    console.log(`\n  ${stage} (${list.length})`);
    for (const [d, count] of [...details].sort((x, y) => y[1] - x[1])) {
      console.log(`    ${String(count).padStart(3)}  ${d}`);
    }
  }

  if (listCases) {
    console.log("\nPer-case attribution:");
    for (const stage of STAGES) {
      const list = byStage.get(stage);
      if (!list?.length) continue;
      console.log(`\n  == ${stage} ==`);
      for (const r of list) {
        console.log(`  ${r.c.id.padEnd(16)} ${r.a.detail}`);
        console.log(`      "${r.c.ask.slice(0, 84)}"`);
        if (r.o.skill) console.log(`      skill: ${r.o.skill}`);
        if (r.a.cascaded.length) console.log(`      cascaded: ${r.a.cascaded.join("; ")}`);
      }
    }
  }
  console.log("");
}

await main();
