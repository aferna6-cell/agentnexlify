#!/usr/bin/env bash
# Cron wrapper for the research skill graph.
# Picks next queued question, runs it, commits result if --auto-commit set.
#
# crontab example (every 6 hours):
#   0 */6 * * * /home/aidan/agentnexlify/research-skill-graph/scripts/run-research.sh --auto-commit >> /tmp/research.log 2>&1

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# prefer project venv if present
if [[ -f "../.venv/bin/python" ]]; then
  PY="../.venv/bin/python"
elif [[ -f ".venv/bin/python" ]]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi

"$PY" scripts/run-research.py "$@"
