/**
 * Architectural guard: the executor is the only way an agent reaches a tool.
 *
 * The whole security model rests on that one boundary — policy, approval,
 * verification and the audit row all live inside `executeAction()`. An agent
 * that imported a tool module directly could call `execute()` and skip every one
 * of them, so this fails CI the moment that happens.
 *
 * Same idea as the engine's "agents never import the Prisma client" guard.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const AGENTS_DIR = join(process.cwd(), "src", "agent-os", "agents");

/** Every .ts file under agents/, recursively, excluding tests. */
function agentSourceFiles(dir: string = AGENTS_DIR): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      out.push(...agentSourceFiles(path));
    } else if (entry.endsWith(".ts") && !entry.endsWith(".test.ts")) {
      out.push(path);
    }
  }
  return out;
}

test("no agent imports a tool module directly", () => {
  const offenders: string[] = [];
  for (const file of agentSourceFiles()) {
    const source = readFileSync(file, "utf8");
    if (/from\s+["'][^"']*actions\/tools\//.test(source)) {
      offenders.push(file.replace(`${process.cwd()}/`, ""));
    }
  }
  assert.deepEqual(
    offenders,
    [],
    `these agent modules import a tool directly instead of going through executeAction(): ${offenders.join(", ")}`,
  );
});

test("no agent calls a tool's execute() itself", () => {
  const offenders: string[] = [];
  for (const file of agentSourceFiles()) {
    const source = readFileSync(file, "utf8");
    // `tool.execute(`, `someTool.execute(` — the call the executor exists to own.
    if (/\b[A-Za-z_$][\w$]*[Tt]ool\.execute\s*\(/.test(source)) {
      offenders.push(file.replace(`${process.cwd()}/`, ""));
    }
  }
  assert.deepEqual(
    offenders,
    [],
    `these agent modules call a tool directly: ${offenders.join(", ")}`,
  );
});

test("the action layer is reached only through the executor's entry points", () => {
  const allowed = new Set([
    "executeAction",
    "hasActionStore",
    "hasToolPorts",
    // Feature-flag reads for M8 resolvers — not tool execution. Policy still
    // enforces the same flags inside evaluateActionPolicy.
    "calendarActionsEnabled",
    "crmActionsEnabled",
  ]);
  const imported = new Set<string>();

  for (const file of agentSourceFiles()) {
    const source = readFileSync(file, "utf8");
    for (const match of source.matchAll(
      /import\s*\{([^}]+)\}\s*from\s*["'][^"']*\/actions\/[^"']+["']/g,
    )) {
      for (const name of match[1]!.split(",")) {
        const cleaned = name
          .trim()
          .replace(/^type\s+/, "")
          .split(/\s+as\s+/)[0]!
          .trim();
        if (cleaned) imported.add(cleaned);
      }
    }
  }

  const unexpected = [...imported].filter(
    (name) => !allowed.has(name) && !/^[A-Z]/.test(name),
  );
  assert.deepEqual(
    unexpected,
    [],
    `agents may only use ${[...allowed].join(", ")} from the action layer; found: ${unexpected.join(", ")}`,
  );
});
