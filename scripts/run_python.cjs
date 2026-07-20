#!/usr/bin/env node
"use strict";

// Cross-platform bootstrap for scripts/run_python.py. npm guarantees Node is
// available, while macOS commonly provides only `python3` and Windows commonly
// provides only `python` or `py -3`.
const { spawnSync } = require("node:child_process");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const requested = process.env.AGENTNEXLIFY_PYTHON;
const candidates = [
  requested ? { command: requested, prefix: [] } : null,
  { command: "python3", prefix: [] },
  { command: "python", prefix: [] },
  { command: "py", prefix: ["-3"] },
].filter(Boolean);

let launcher = null;
for (const candidate of candidates) {
  const probe = spawnSync(candidate.command, [...candidate.prefix, "--version"], {
    cwd: root,
    encoding: "utf8",
  });
  if (!probe.error && probe.status === 0) {
    launcher = candidate;
    break;
  }
}

if (!launcher) {
  console.error("No Python 3 interpreter found. Set AGENTNEXLIFY_PYTHON to its path.");
  process.exit(1);
}

const result = spawnSync(
  launcher.command,
  [...launcher.prefix, "scripts/run_python.py", ...process.argv.slice(2)],
  { cwd: root, stdio: "inherit" },
);
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
