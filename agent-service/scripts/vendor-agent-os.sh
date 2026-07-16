#!/usr/bin/env bash
#
# RETIRED (2026-07-16). Do not run.
#
# This script used to vendor the Agent OS engine from the standalone
# Agent-Nexlify-OS repo, which was the source of truth at the time. That repo
# has since been transferred INTO this one: `agent-service/src/agent-os` in
# THIS repo is the canonical, actively-developed engine, and the standalone
# repo is stale. Engine changes are made directly here (with `npm run
# typecheck && npm test` in agent-service/) and reviewed through this repo's
# PRs.
#
# The old behavior was destructive by design (`rm -rf src/agent-os`, then copy
# from the standalone) - running it against the stale repo would silently wipe
# every engine change made here since the transfer (e.g. the market_research
# skill and its tests). Hence the hard stop below rather than a warning.
#
# Kept in-tree so `npm run vendor:agent-os` fails loudly with this explanation
# instead of "command not found" archaeology. Full history: git log on this
# file.
set -euo pipefail

echo "error: vendor-agent-os.sh is retired." >&2
echo "The standalone Agent-Nexlify-OS repo was transferred into this repo;" >&2
echo "agent-service/src/agent-os is the source of truth now. Edit the engine" >&2
echo "directly here - re-vendoring would wipe changes made since the transfer." >&2
exit 1
