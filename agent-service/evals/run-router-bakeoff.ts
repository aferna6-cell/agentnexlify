/**
 * Milestone 6 router bakeoff predictor — heuristic (and optional Haiku).
 *
 * Writes candidate lists for validation-v3. Does not change production routing.
 * Frozen 215 is not used here.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  classifyHeuristic,
  classifyWithHaiku,
  type Candidate,
} from "../src/agent-os/agents/_classifier.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const V3 = join(HERE, "datasets", "validation", "validation-v3.json");
const OUT_DIR = join(HERE, "..", "..", "ml", "routing", "bakeoff", "artifacts");

interface V3Case {
  id: string;
  ask: string;
  expected_department: string;
  acceptable_departments?: string[];
}

const wantHaiku =
  process.argv.includes("--haiku") && Boolean(process.env.ANTHROPIC_API_KEY);
const dataset = JSON.parse(readFileSync(V3, "utf8")) as { cases: V3Case[] };

const heuristic: Record<string, Candidate[]> = {};
const haiku: Record<string, Candidate[]> = {};

for (const c of dataset.cases) {
  heuristic[c.ask] = classifyHeuristic(c.ask).candidates;
  if (wantHaiku) {
    const live = await classifyWithHaiku(c.ask);
    if (live) haiku[c.ask] = live.candidates;
  }
}

mkdirSync(OUT_DIR, { recursive: true });
writeFileSync(
  join(OUT_DIR, "heuristic-v3.json"),
  JSON.stringify(heuristic, null, 2) + "\n",
);
if (wantHaiku) {
  writeFileSync(
    join(OUT_DIR, "haiku-v3.json"),
    JSON.stringify(haiku, null, 2) + "\n",
  );
}

console.log(
  `wrote ${Object.keys(heuristic).length} heuristic predictions to ${OUT_DIR}`,
);
if (!wantHaiku)
  console.log("haiku skipped (no --haiku or no ANTHROPIC_API_KEY)");
