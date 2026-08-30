/**
 * Read-only replay of one ask. No --send, --approve, --yes, or --force.
 * Approval is an owner act against a durable row, not a CLI flag.
 */

import { goOffline } from "./lib/offline.ts";
goOffline();

import { readAskIntent } from "../src/agent-os/agents/_intent.ts";
import { classifyHeuristic } from "../src/agent-os/agents/_classifier.ts";

const ask = process.argv.slice(2).join(" ").trim();
if (!ask) {
  console.error('usage: npm run eval:inspect -- "<owner ask>"');
  process.exit(2);
}

const intent = readAskIntent(ask);
const cls = classifyHeuristic(ask);
console.log(JSON.stringify({ ask, intent, classification: cls }, null, 2));
