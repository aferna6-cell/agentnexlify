/**
 * Read-only replay of one ask. This CLI never flips the live-send flag
 * and never claims an approval. Approval is an owner act against a
 * durable row, not something this process can grant.
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
