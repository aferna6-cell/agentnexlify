/**
 * M9: workflow modules must not import Action Executor / tool implementations.
 * Mirrors scripts/check_project_invariants.check_workflow_planner_import_boundary.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const WORKFLOWS_DIR = join(process.cwd(), "src", "agent-os", "workflows");

const FORBIDDEN = [
  /actions\/executor/,
  /actions\/tools\//,
  /GmailMailboxPort/,
  /CalendarPort/,
];

function sourceFiles(dir: string = WORKFLOWS_DIR): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      out.push(...sourceFiles(path));
    } else if (entry.endsWith(".ts") && !entry.endsWith(".test.ts")) {
      out.push(path);
    }
  }
  return out;
}

test("workflow modules do not import Action Executor or tool modules", () => {
  const offenders: string[] = [];
  for (const file of sourceFiles()) {
    const source = readFileSync(file, "utf8");
    for (const pattern of FORBIDDEN) {
      if (pattern.test(source)) {
        offenders.push(file.replace(`${process.cwd()}/`, ""));
        break;
      }
    }
  }
  assert.deepEqual(offenders, [], `forbidden imports: ${offenders.join(", ")}`);
});
