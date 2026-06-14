#!/usr/bin/env bash
#
# Vendor the Agent OS engine from the standalone repo into agent-service.
#
# The standalone (Agent-Nexlify-OS) is the SOURCE OF TRUTH for the agent engine.
# agent-service runs that engine under `node --experimental-strip-types`, which
# (unlike the standalone's bundler) does NOT rewrite ".js" import specifiers to
# their ".ts" siblings — so this script copies the engine verbatim and rewrites
# relative ".js" specifiers to ".ts" to match the agent-service runtime.
#
# It also (re)emits the three environment-specific wiring files that differ from
# the standalone: agents/_shared-context.ts (loadSharedContext only — no Prisma),
# agents/_run-store.ts (no-op — startup registers the HTTP store), and
# lib/usage.ts (no caps — the data plane meters usage). These three plus the
# dropped lib/db.ts are the ONLY places the agent-service diverges from upstream.
#
# This is a dev-only operation: the standalone repo is not present in CI/Railway.
# What ships is the committed output of this script. Re-run after pulling engine
# changes from the standalone, then run `npm run typecheck && npm test`.
#
# Usage:  AGENT_OS_SRC=/path/to/Agent-Nexlify-OS bash scripts/vendor-agent-os.sh
set -euo pipefail

SRC="${AGENT_OS_SRC:-$(cd "$(dirname "$0")/../.." && pwd)/../Agent-Nexlify-OS}/src"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HERE/src/agent-os"

if [ ! -d "$SRC/agents" ]; then
  echo "error: standalone source not found at $SRC (set AGENT_OS_SRC)" >&2
  exit 1
fi

echo "vendoring engine from $SRC -> $DEST"
rm -rf "$DEST"
mkdir -p "$DEST/lib/providers" "$DEST/types"

# Engine (verbatim) ----------------------------------------------------------
cp -r "$SRC/agents" "$DEST/agents"
cp "$SRC/types/agent.ts" "$DEST/types/agent.ts"
cp "$SRC/lib/anthropic.ts" "$SRC/lib/draft.ts" "$SRC/lib/seo.ts" "$DEST/lib/"
cp "$SRC/lib/providers/owner-actions.ts" "$SRC/lib/providers/run-store.ts" \
   "$SRC/lib/providers/shared-context.ts" "$DEST/lib/providers/"

# Prune: tests + the env-specific wiring files we replace below --------------
find "$DEST" -name '*.test.ts' -delete
rm -f "$DEST/agents/_shared-context.ts" "$DEST/agents/_run-store.ts"

# Rewrite relative ".js" import specifiers -> ".ts" for node strip-types -----
find "$DEST" -name '*.ts' -print0 | xargs -0 sed -i -E \
  -e 's#(from[[:space:]]+"\.[^"]*)\.js"#\1.ts"#g' \
  -e 's#(import\("\.[^"]*)\.js"#\1.ts"#g' \
  -e 's#(import[[:space:]]+"\.[^"]*)\.js"#\1.ts"#g'

# Wiring files (agent-service-specific) -------------------------------------
cat > "$DEST/agents/_shared-context.ts" <<'TS'
/**
 * Shared-context wiring for the agent-service runtime.
 *
 * The standalone registers a Prisma provider here; the agent-service registers
 * its production SharedContextProvider at startup (reading the FastAPI/Supabase
 * data plane, scoped by client_id). This module only keeps `loadSharedContext()`
 * as the stable accessor the orchestrator imports — identical signature to the
 * standalone, so the vendored orchestrator is unchanged.
 */

import { getSharedContextProvider } from "../lib/providers/shared-context.ts";
import type { SharedContext } from "../types/agent.ts";

export async function loadSharedContext(userId: string): Promise<SharedContext> {
  return getSharedContextProvider().load(userId);
}
TS

cat > "$DEST/agents/_run-store.ts" <<'TS'
/**
 * RunStore wiring for the agent-service runtime.
 *
 * The orchestrator imports this module for the side effect that, in the
 * standalone, registers PrismaRunStore. In the agent-service the RunStore is
 * registered explicitly at startup (an HTTP store that persists into the
 * FastAPI/Supabase `os_*` data plane), so this module intentionally registers
 * nothing. Kept so the vendored orchestrator's `import "./_run-store.ts"`
 * resolves unchanged.
 */

export {};
TS

cat > "$DEST/lib/usage.ts" <<'TS'
/**
 * Usage caps — no-op in the agent-service runtime.
 *
 * The standalone enforced a daily demo-spend cap by counting ModelCallLog rows
 * in Prisma. In production, usage metering and caps live in the FastAPI data
 * plane (os_tenant_usage / ai_usage_guard), so the engine never gates itself
 * here. `anthropic.ts` imports `isCapExceeded()`; it always reports "not
 * exceeded" and the data plane refuses over-budget tenants before it ever calls
 * the orchestrator.
 */

export const ROUTING_CAP = Number(process.env.USAGE_CAP_ROUTING ?? 0);
export const DRAFT_CAP = Number(process.env.USAGE_CAP_DRAFT ?? 0);

export async function isCapExceeded(_purpose: "routing" | "draft" | "other"): Promise<boolean> {
  return false;
}
TS

# Guard: the agent-service runs under `node --experimental-strip-types`, which
# rejects transform-only TS (parameter properties, enums, namespaces). Fail loudly
# here so a re-vendor can never silently ship code that crashes at runtime.
if grep -rnE 'constructor\([^)]*(public|private|protected|readonly)|^\s*(export\s+)?(enum|namespace)\s+[A-Za-z]' "$DEST"; then
  echo "error: transform-only TS syntax above must be refactored in the standalone source" >&2
  exit 1
fi

echo "done. files: $(find "$DEST" -name '*.ts' | wc -l)"
