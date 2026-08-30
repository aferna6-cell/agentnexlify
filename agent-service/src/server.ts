/**
 * Minimal HTTP server for agent-service.
 *
 * Routes:
 *   GET  /health             -> 200 {"status":"ok"}
 *   POST /orchestrate        -> one Agent OS turn (result + persistable record)
 *   POST /actions/approve    -> execute an action the owner approved
 *   POST /agents/:name/run   -> RunResult JSON
 *
 * Request body for /agents/:name/run:
 *   { "prompt": "...", "timeout_ms": 30000 }
 *
 * No external HTTP framework — plain node:http to keep the image small.
 */

import {
  createServer,
  type IncomingMessage,
  type ServerResponse,
} from "node:http";
import { runAgent } from "./runner.ts";
import { runOrchestration } from "./agent-os-runtime/orchestrate.ts";
import {
  runApprovedAction,
  PendingExecutionSchema,
} from "./agent-os-runtime/approve-action.ts";
import type { TenantToolPolicy } from "./agent-os/actions/policy.ts";
import type { CustomerNoteRecord } from "./agent-os/actions/ports.ts";
import { isTokenAuthorized } from "./auth.ts";
import type { SharedContext } from "./agent-os/types/agent.ts";

const PORT = parseInt(process.env.PORT ?? "3100", 10);

// Optional shared secret. When AGENT_SERVICE_TOKEN is set, every request to a
// compute route must carry a matching X-Agent-Token header. This is
// defense-in-depth on top of Railway private networking: even with a public
// domain, the engine is not an open endpoint anyone can drive to burn credits.
// Unset = open mode (local dev / parity with the prior behavior). /health is
// never guarded so Railway's healthcheck keeps working.
const AGENT_SERVICE_TOKEN = process.env.AGENT_SERVICE_TOKEN ?? "";

/** True when the request is authorized (token unset, or header matches). */
function isAuthorized(req: IncomingMessage): boolean {
  return isTokenAuthorized(req.headers["x-agent-token"], AGENT_SERVICE_TOKEN);
}

async function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk: Buffer) => {
      data += chunk.toString("utf8");
    });
    req.on("end", () => resolve(data));
    req.on("error", reject);
  });
}

function json(res: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(payload),
  });
  res.end(payload);
}

/** Extract :name from /agents/:name/run, or null if path does not match. */
function parseAgentName(url: string): string | null {
  const parts = url.split("/");
  // Expect ['', 'agents', '<name>', 'run']
  if (parts.length === 4 && parts[1] === "agents" && parts[3] === "run") {
    const name = parts[2];
    // Validate: lowercase alphanumeric + hyphens only
    if (/^[a-z0-9-]+$/.test(name)) return name;
  }
  return null;
}

const server = createServer(
  async (req: IncomingMessage, res: ServerResponse) => {
    try {
      if (req.method === "GET" && req.url === "/health") {
        json(res, 200, { status: "ok" });
        return;
      }

      // All compute routes below require the shared secret when one is configured.
      if (!isAuthorized(req)) {
        json(res, 401, { error: "unauthorized" });
        return;
      }

      // Agent OS orchestration. FastAPI (the data plane) authenticates the tenant,
      // assembles its SharedContext from Supabase, and POSTs it here; agent-service
      // runs the engine and returns the result + a record for FastAPI to persist.
      // agent-service never touches a database.
      if (req.method === "POST" && req.url === "/orchestrate") {
        const raw = await readBody(req);
        let body: {
          accountId?: unknown;
          ask?: unknown;
          context?: unknown;
          forceAgentId?: unknown;
          requestOrigin?: unknown;
          toolPolicy?: unknown;
        };
        try {
          body = JSON.parse(raw) as typeof body;
        } catch {
          json(res, 400, { error: "invalid JSON body" });
          return;
        }
        if (typeof body.accountId !== "string" || !body.accountId.trim()) {
          json(res, 400, { error: "accountId must be a non-empty string" });
          return;
        }
        if (typeof body.ask !== "string" || !body.ask.trim()) {
          json(res, 400, { error: "ask must be a non-empty string" });
          return;
        }
        if (typeof body.context !== "object" || body.context === null) {
          json(res, 400, {
            error: "context must be the tenant SharedContext object",
          });
          return;
        }
        if (
          body.forceAgentId !== undefined &&
          typeof body.forceAgentId !== "string"
        ) {
          json(res, 400, {
            error: "forceAgentId must be a string when provided",
          });
          return;
        }
        if (
          body.requestOrigin === undefined ||
          !["owner", "inbound", "system"].includes(String(body.requestOrigin))
        ) {
          json(res, 400, {
            error: "requestOrigin must be owner, inbound, or system",
          });
          return;
        }
        if (
          body.toolPolicy !== undefined &&
          (typeof body.toolPolicy !== "object" || body.toolPolicy === null)
        ) {
          json(res, 400, {
            error: "toolPolicy must be an object when provided",
          });
          return;
        }
        const out = await runOrchestration({
          accountId: body.accountId,
          ask: body.ask,
          context: body.context as SharedContext,
          forceAgentId: body.forceAgentId,
          requestOrigin: body.requestOrigin as
            "owner" | "inbound" | "system" | undefined,
          toolPolicy: body.toolPolicy as TenantToolPolicy | undefined,
        });
        json(res, 200, out);
        return;
      }

      // Action approval. The data plane owns the durable execution row and has
      // already decided (with a conditional UPDATE) that THIS call is the one that
      // runs; the engine executes it through the same executor an agent uses, so
      // policy, verification and the audit record behave identically.
      if (req.method === "POST" && req.url === "/actions/approve") {
        const raw = await readBody(req);
        let body: {
          accountId?: unknown;
          execution?: unknown;
          context?: unknown;
          approvedBy?: unknown;
          toolPolicy?: unknown;
          existingNotes?: unknown;
        };
        try {
          body = JSON.parse(raw) as typeof body;
        } catch {
          json(res, 400, { error: "invalid JSON body" });
          return;
        }
        if (typeof body.accountId !== "string" || !body.accountId.trim()) {
          json(res, 400, { error: "accountId must be a non-empty string" });
          return;
        }
        if (typeof body.approvedBy !== "string" || !body.approvedBy.trim()) {
          json(res, 400, { error: "approvedBy must be a non-empty string" });
          return;
        }
        if (typeof body.context !== "object" || body.context === null) {
          json(res, 400, {
            error: "context must be the tenant SharedContext object",
          });
          return;
        }
        const parsed = PendingExecutionSchema.safeParse(body.execution);
        if (!parsed.success) {
          json(res, 400, {
            error: "execution is not a valid stored action execution",
            detail: parsed.error.issues.map(
              (i) => `${i.path.join(".") || "execution"}: ${i.message}`,
            ),
          });
          return;
        }
        if (parsed.data.accountId !== body.accountId) {
          json(res, 403, { error: "execution belongs to another account" });
          return;
        }
        const out = await runApprovedAction({
          accountId: body.accountId,
          execution: parsed.data,
          context: body.context as SharedContext,
          approvedBy: body.approvedBy,
          toolPolicy: (body.toolPolicy ?? undefined) as
            TenantToolPolicy | undefined,
          existingNotes: (body.existingNotes ?? undefined) as
            CustomerNoteRecord[] | undefined,
        });
        json(res, 200, out);
        return;
      }

      const agentName = parseAgentName(req.url ?? "");
      if (!agentName || req.method !== "POST") {
        json(res, 404, { error: "not found" });
        return;
      }

      const rawBody = await readBody(req);

      let payload: { prompt?: unknown; timeout_ms?: unknown };
      try {
        payload = JSON.parse(rawBody) as {
          prompt?: unknown;
          timeout_ms?: unknown;
        };
      } catch {
        json(res, 400, { error: "invalid JSON body" });
        return;
      }

      if (typeof payload.prompt !== "string" || !payload.prompt.trim()) {
        json(res, 400, { error: "prompt must be a non-empty string" });
        return;
      }

      const timeoutMs =
        typeof payload.timeout_ms === "number" && payload.timeout_ms > 0
          ? payload.timeout_ms
          : undefined;

      const result = await runAgent(agentName, payload.prompt, timeoutMs);
      json(res, 200, result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      console.error("agent-service: unhandled error:", err);
      json(res, 500, { error: message });
    }
  },
);

server.listen(PORT, () => {
  console.log(
    `agent-service: listening on :${PORT} (REPO_ROOT=${process.env.REPO_ROOT ?? "(auto)"})`,
  );
});
